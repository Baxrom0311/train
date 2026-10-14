"""
Nomzodlar qidiruvi va vakansiya mosligi — `talent_profiles` ustida SQL (CONTRACT.md §33.3).

Filtr, saralash va sahifalash Postgres'da: so'rov nomzodlar sonidan qat'i nazar
faqat kerakli sahifani o'qiydi va Run'larga tegmaydi. Moslik formulasi
(`fit_expr`, `meets_expr`) `talent/vacancies.py`dagi `fit` bilan bir xil (§23.2) —
tanlov va tartib SQL'da, javobdagi `fit` va `gaps` shu topilgan profillar uchun
Python'da hisoblanadi.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import Float, Numeric, Select, and_, cast, false, func, literal, not_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer
from sqlalchemy.sql.elements import ColumnElement

from app.models.talent import CandidateVisibility, TalentProfile, Vacancy
from app.models.user import User
from app.talent.profile import Profile
from app.talent.vacancies import MATCH_MIN_FIT, MAX_MATCHES

Candidate = tuple[User, Profile]


def visible_to(company_id: uuid.UUID) -> Select:
    """Shu kompaniyaga ko'rinadigan nomzodlar id'lari (§5: yozuv yo'q = yopiq, yashirilgan = yo'q)."""
    hidden = cast(CandidateVisibility.hidden_from_company_ids, JSONB)
    return select(CandidateVisibility.user_id).where(
        CandidateVisibility.is_open_to_work.is_(True),
        not_(hidden.contains(func.jsonb_build_array(str(company_id)))),
    )


def _visible(company_id: uuid.UUID) -> Select:
    """Ko'rinadigan, faol, profili bor nomzodlar — Run ro'yxatisiz (kartaga kerak emas)."""
    return (
        select(TalentProfile, User)
        .join(User, User.id == TalentProfile.user_id)
        .where(TalentProfile.user_id.in_(visible_to(company_id)), User.is_active.is_(True))
        .options(defer(TalentProfile.runs))
        .execution_options(populate_existing=True)
    )


def _rows(result) -> list[Candidate]:
    return [(user, Profile.from_row(row, runs=False)) for row, user in result.all()]


def _competency(key: str, type_=Float) -> ColumnElement:
    return cast(TalentProfile.competencies[key].astext, type_)


def _overall_or(default: float) -> ColumnElement:
    return func.coalesce(TalentProfile.overall_score, default)


# ---------------------------------------------------------------------------
# Kompaniya: nomzodlar ro'yxati (§10.4), hisobot va CSV (§20)
# ---------------------------------------------------------------------------

async def search(
    db: AsyncSession, company_id: uuid.UUID, *, sector: str | None, competency: str | None,
    min_score: float, recent: bool, limit: int, offset: int,
) -> tuple[list[Candidate], int]:
    """
    §10.4: ball — tanlangan kompetensiya bo'yicha, aks holda umumiy; balli yo'q
    nomzod `min_score=0`da ham chiqmaydi (ball -1 hisoblanadi). Teng holatda — `user_id`
    (sahifalar orasida nomzod takrorlanmaydi va tushib qolmaydi).
    """
    score = _competency(competency) if competency else TalentProfile.overall_score
    score = func.coalesce(score, -1)
    q = _visible(company_id).where(score >= min_score)
    if sector is not None:
        q = q.where(TalentProfile.sectors.contains([sector]))
    if competency is not None:
        q = q.where(TalentProfile.competencies.has_key(competency))

    total = await db.scalar(select(func.count()).select_from(q.order_by(None).subquery()))
    if recent:
        q = q.order_by(TalentProfile.last_completed_at.desc(), TalentProfile.user_id)
    else:
        q = q.order_by(score.desc(), TalentProfile.last_completed_at.desc(), TalentProfile.user_id)
    return _rows(await db.execute(q.limit(limit).offset(offset))), total or 0


async def visible_candidates(db: AsyncSession, company_id: uuid.UUID) -> list[Candidate]:
    """Kompaniyaga ko'rinadigan barcha nomzodlar, ball bo'yicha (hisobot va CSV, §20)."""
    q = _visible(company_id).order_by(
        _overall_or(-1).desc(), TalentProfile.last_completed_at.desc(), TalentProfile.user_id,
    )
    return _rows(await db.execute(q))


# ---------------------------------------------------------------------------
# Vakansiya mosligi (§23.2, §23.3)
# ---------------------------------------------------------------------------

def fit_expr(vacancy: Vacancy) -> ColumnElement:
    """`vacancies.fit().fit`: talablar bo'yicha `min(1, ball / talab)` o'rtachasi ×100, 0.1 gacha (half-up)."""
    requirements: dict[str, int] = vacancy.requirements or {}
    if not requirements:
        return _overall_or(0)
    one = literal(Decimal(1), Numeric)
    ratios = [
        one if required <= 0 else func.least(one, func.coalesce(_competency(key, Numeric), 0) / required)
        for key, required in requirements.items()
    ]
    return func.round(sum(ratios[1:], ratios[0]) * 100 / len(ratios), 1)


def meets_expr(vacancy: Vacancy) -> ColumnElement | None:
    """
    `vacancies.fit().meets`: har talab bajarilgan va umumiy ball ≥ `min_score` (agar berilgan bo'lsa).
    Shart yo'q — `None` (hamma mos; Postgres ORDER BY'da doimiy qiymatni qabul qilmaydi).
    """
    conditions = [
        func.coalesce(_competency(key), 0) >= required
        for key, required in (vacancy.requirements or {}).items()
    ]
    if vacancy.min_score is not None:
        conditions.append(TalentProfile.overall_score >= vacancy.min_score)
    # balli yo'q nomzodda taqqoslash NULL — "mos emas"
    return func.coalesce(and_(*conditions), false()) if conditions else None


async def matches(db: AsyncSession, company_id: uuid.UUID, vacancy: Vacancy) -> list[Candidate]:
    """§23.3: ko'rinadigan nomzodlar, fit ≥ 50, mos — oldin, keyin fit, soha, umumiy ball; ≤ 50 ta."""
    fit = fit_expr(vacancy)
    meets = meets_expr(vacancy)
    order = [] if meets is None else [meets.desc()]
    order += [fit.desc(), TalentProfile.sectors.contains([vacancy.sector.value]).desc(), _overall_or(-1).desc(),
              TalentProfile.user_id]
    q = _visible(company_id).where(fit >= MATCH_MIN_FIT).order_by(*order).limit(MAX_MATCHES)
    return _rows(await db.execute(q))


def _count_meeting(vacancy: Vacancy) -> ColumnElement:
    meets = meets_expr(vacancy)
    return func.count() if meets is None else func.count().filter(meets)


async def match_counts(db: AsyncSession, company_id: uuid.UUID, vacancies: list[Vacancy]) -> dict[uuid.UUID, int]:
    """Har vakansiyaga talablarni to'liq bajaradigan ko'rinadigan nomzodlar soni — bitta so'rovda (§23.5)."""
    if not vacancies:
        return {}
    q = (
        select(*(_count_meeting(v) for v in vacancies))
        .select_from(TalentProfile)
        .join(User, User.id == TalentProfile.user_id)
        .where(TalentProfile.user_id.in_(visible_to(company_id)), User.is_active.is_(True))
    )
    counts = (await db.execute(q)).one()
    return {v.id: n for v, n in zip(vacancies, counts)}
