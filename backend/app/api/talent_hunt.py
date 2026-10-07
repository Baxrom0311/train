"""
Talent Hunt API — CONTRACT.md §5 (maxfiylik) va §10 (Run natijalari, takliflar).
Modul 4 egaligi: backend/app/api/talent_hunt.py, backend/app/talent/.

Maxfiylik: `candidate_visibility` yozuvi yo'q yoki `is_open_to_work=false`
bo'lgan, yoki kompaniyani yashirgan nomzod kompaniya uchun mavjud emas —
har doim 404, hech qachon "yashirilgan" emas.
"""
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import cast, func, not_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_permission
from app.database import get_db
from app.models.billing import Company
from app.models.enums import Competency, OfferResponse, OrgType, Sector, TalentOfferStatus
from app.models.talent import CandidateVisibility, TalentOffer
from app.models.user import User
from app.scenario.clock import WorkCalendar
from app.talent.profile import Profile, build_profiles

router = APIRouter(prefix="/api/v1/talents", tags=["Talent Hunt"])
users_router = APIRouter(prefix="/api/v1/users", tags=["Talent Hunt - Visibility"])

RESPOND_WORKDAYS = 5
OPEN_STATUSES = (TalentOfferStatus.SENT, TalentOfferStatus.VIEWED)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Schemalar
# ---------------------------------------------------------------------------

class VisibilityUpdate(BaseModel):
    is_open_to_work: bool
    hidden_from_company_ids: list[uuid.UUID] = Field(default_factory=list, max_length=200)


class VisibilityOut(BaseModel):
    is_open_to_work: bool
    hidden_from_company_ids: list[str]


class RunSummaryOut(BaseModel):
    scenario_title: str
    company_name: str
    sector: str
    completed_at: datetime
    overall_score: float | None
    competency_scores: dict[str, float]
    strengths: list[str]


class CandidateCard(BaseModel):
    """Kontakt (email) yo'q — u faqat talaba taklifni qabul qilganda ochiladi (§10.2)."""
    id: uuid.UUID
    full_name: str
    overall_score: float | None
    runs_completed: int
    sectors: list[str]
    top_competencies: dict[str, float]
    last_completed_at: datetime | None


class CandidateProfile(CandidateCard):
    competencies: dict[str, float]
    runs: list[RunSummaryOut]


class CandidatePage(BaseModel):
    items: list[CandidateCard]
    total: int


class TalentOfferCreate(BaseModel):
    candidate_user_id: uuid.UUID
    position_title: str = Field(min_length=2, max_length=120)
    message: str = Field(min_length=10, max_length=2000)


class TalentOfferOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    candidate_user_id: uuid.UUID
    position_title: str
    message: str
    status: TalentOfferStatus
    response: OfferResponse | None
    response_note: str | None
    respond_due_at: datetime | None
    responded_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SentOfferOut(TalentOfferOut):
    candidate_name: str
    candidate_email: str | None  # faqat accepted'da


class ReceivedOfferOut(TalentOfferOut):
    company_name: str
    company_industry: str


class OfferRespond(BaseModel):
    decision: OfferResponse
    note: str | None = Field(default=None, max_length=500)
    # rad etib, shu kompaniyadan yashirinish (§10.2)
    hide_company: bool = False


class SortBy(str, Enum):
    SCORE = "score"
    RECENT = "recent"


# ---------------------------------------------------------------------------
# Yordamchilar
# ---------------------------------------------------------------------------

async def verified_company(
    current_user: Annotated[User, Depends(require_permission("view_candidates"))],
    db: AsyncSession = Depends(get_db),
) -> Company:
    """`view_candidates` + foydalanuvchi tasdiqlangan kompaniyaga tegishli (§10.3)."""
    if current_user.org_type != OrgType.COMPANY or not current_user.org_id:
        raise HTTPException(status_code=403, detail="Only company users can access candidates")
    company = await db.get(Company, current_user.org_id)
    if not company or not company.is_verified:
        raise HTTPException(status_code=403, detail="Company is not verified")
    return company


Candidate = Annotated[User, Depends(require_permission("receive_offers"))]
VerifiedCompany = Annotated[Company, Depends(verified_company)]


def _visible_to(company_id: uuid.UUID):
    """Shu kompaniyaga ko'rinadigan nomzodlar id'lari (INNER JOIN — yozuv yo'q = yopiq)."""
    hidden = cast(CandidateVisibility.hidden_from_company_ids, JSONB)
    return select(CandidateVisibility.user_id).where(
        CandidateVisibility.is_open_to_work.is_(True),
        not_(hidden.contains(func.jsonb_build_array(str(company_id)))),
    )


def _card(user: User, p: Profile) -> CandidateCard:
    return CandidateCard(
        id=user.id,
        full_name=user.full_name,
        overall_score=p.overall_score,
        runs_completed=len(p.runs),
        sectors=p.sectors,
        top_competencies=p.top_competencies,
        last_completed_at=p.last_completed_at,
    )


def _profile(user: User, p: Profile) -> CandidateProfile:
    return CandidateProfile(
        **_card(user, p).model_dump(),
        competencies=p.competencies,
        runs=[RunSummaryOut(**{k: getattr(r, k) for k in RunSummaryOut.model_fields}) for r in p.runs],
    )


async def _visible_candidate(db: AsyncSession, company: Company, user_id: uuid.UUID) -> tuple[User, Profile]:
    """Shu kompaniyaga ko'rinadigan, faol va profili bor nomzod; aks holda 404."""
    visible = _visible_to(company.id).where(CandidateVisibility.user_id == user_id)
    p = (await build_profiles(db, visible)).get(user_id)
    user = await db.get(User, user_id) if p else None
    if p is None or user is None or not user.is_active:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return user, p


async def _visibility(db: AsyncSession, user_id: uuid.UUID, *, lock: bool = False) -> CandidateVisibility | None:
    q = select(CandidateVisibility).where(CandidateVisibility.user_id == user_id)
    if lock:
        q = q.with_for_update()
    return (await db.execute(q)).scalars().first()


def _visibility_out(vis: CandidateVisibility | None) -> VisibilityOut:
    if vis is None:
        return VisibilityOut(is_open_to_work=False, hidden_from_company_ids=[])
    return VisibilityOut(is_open_to_work=vis.is_open_to_work, hidden_from_company_ids=list(vis.hidden_from_company_ids or []))


async def _hide_company(db: AsyncSession, user_id: uuid.UUID, company_id: uuid.UUID) -> None:
    vis = await _visibility(db, user_id, lock=True)
    if vis is None:
        vis = CandidateVisibility(user_id=user_id, is_open_to_work=False, hidden_from_company_ids=[])
        db.add(vis)
    hidden = list(vis.hidden_from_company_ids or [])
    if str(company_id) not in hidden:
        vis.hidden_from_company_ids = [*hidden, str(company_id)]
        vis.updated_at = _now()


async def _my_offer(db: AsyncSession, offer_id: uuid.UUID, user: User) -> TalentOffer:
    offer = (await db.execute(
        select(TalentOffer).where(TalentOffer.id == offer_id).with_for_update()
    )).scalars().first()
    if offer is None or offer.candidate_user_id != user.id:
        raise HTTPException(status_code=404, detail="Offer not found")
    return offer


# ---------------------------------------------------------------------------
# Talaba: ko'rinish va o'z profili
# ---------------------------------------------------------------------------

@users_router.get("/me/visibility", response_model=VisibilityOut)
async def get_my_visibility(current_user: Candidate, db: AsyncSession = Depends(get_db)):
    return _visibility_out(await _visibility(db, current_user.id))


@users_router.patch("/me/visibility", response_model=VisibilityOut)
async def update_my_visibility(body: VisibilityUpdate, current_user: Candidate, db: AsyncSession = Depends(get_db)):
    """Talaba o'zining ko'rinishini boshqaradi (CONTRACT.md §5, opt-in)."""
    vis = await _visibility(db, current_user.id, lock=True)
    hidden = list(dict.fromkeys(str(c) for c in body.hidden_from_company_ids))
    if vis is None:
        vis = CandidateVisibility(user_id=current_user.id)
        db.add(vis)
    vis.is_open_to_work = body.is_open_to_work
    vis.hidden_from_company_ids = hidden
    vis.updated_at = _now()
    await db.commit()
    return _visibility_out(vis)


@users_router.get("/me/talent-profile", response_model=CandidateProfile | None)
async def get_my_talent_profile(current_user: Candidate, db: AsyncSession = Depends(get_db)):
    """Kompaniyalar ko'radigan profil; tugallangan Run bo'lmasa — null."""
    p = (await build_profiles(db, [current_user.id])).get(current_user.id)
    return _profile(current_user, p) if p else None


# ---------------------------------------------------------------------------
# Kompaniya: nomzodlar
# ---------------------------------------------------------------------------

@router.get("", response_model=CandidatePage)
async def get_talents(
    company: VerifiedCompany,
    db: AsyncSession = Depends(get_db),
    sector: Sector | None = None,
    competency: Competency | None = None,
    min_score: float = Query(default=0, ge=0, le=100),
    sort: SortBy = SortBy.SCORE,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Ko'rinadigan, kamida bitta tugallangan Run'i bor nomzodlar (§10.4)."""
    profiles = await build_profiles(db, _visible_to(company.id))
    if not profiles:
        return CandidatePage(items=[], total=0)
    users = {u.id: u for u in (await db.execute(
        select(User).where(User.id.in_(profiles.keys()), User.is_active.is_(True))
    )).scalars()}

    def score(p: Profile) -> float:
        value = p.competencies.get(competency.value) if competency else p.overall_score
        return value if value is not None else -1

    matched = [
        p for p in profiles.values()
        if p.user_id in users
        and (sector is None or sector.value in p.sectors)
        and (competency is None or competency.value in p.competencies)
        and score(p) >= min_score
    ]
    if sort == SortBy.RECENT:
        matched.sort(key=lambda p: p.last_completed_at, reverse=True)
    else:
        matched.sort(key=lambda p: (score(p), p.last_completed_at), reverse=True)

    page = matched[offset:offset + limit]
    return CandidatePage(items=[_card(users[p.user_id], p) for p in page], total=len(matched))


@router.get("/offers/sent", response_model=list[SentOfferOut])
async def get_sent_offers(company: VerifiedCompany, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(TalentOffer, User)
        .join(User, User.id == TalentOffer.candidate_user_id)
        .where(TalentOffer.company_id == company.id)
        .order_by(TalentOffer.created_at.desc())
    )).all()
    return [
        SentOfferOut(
            **TalentOfferOut.model_validate(offer).model_dump(),
            candidate_name=user.full_name,
            candidate_email=user.email if offer.response == OfferResponse.ACCEPTED else None,
        )
        for offer, user in rows
    ]


@router.get("/offers/my", response_model=list[ReceivedOfferOut])
async def get_my_offers(current_user: Candidate, db: AsyncSession = Depends(get_db)):
    """Talabaga kelgan takliflar, yangilari tepada."""
    rows = (await db.execute(
        select(TalentOffer, Company)
        .join(Company, Company.id == TalentOffer.company_id)
        .where(TalentOffer.candidate_user_id == current_user.id)
        .order_by(TalentOffer.created_at.desc())
    )).all()
    return [
        ReceivedOfferOut(
            **TalentOfferOut.model_validate(offer).model_dump(),
            company_name=company.name,
            company_industry=company.industry,
        )
        for offer, company in rows
    ]


@router.get("/{user_id}", response_model=CandidateProfile)
async def get_talent(user_id: uuid.UUID, company: VerifiedCompany, db: AsyncSession = Depends(get_db)):
    return _profile(*await _visible_candidate(db, company, user_id))


# ---------------------------------------------------------------------------
# Takliflar
# ---------------------------------------------------------------------------

@router.post("/offers", response_model=TalentOfferOut, status_code=status.HTTP_201_CREATED)
async def create_talent_offer(offer_in: TalentOfferCreate, company: VerifiedCompany, db: AsyncSession = Depends(get_db)):
    """
    Faqat ko'rinadigan va profili bor nomzodga. Yo'q, yopiq yoki yashirilgan —
    barchasi 404 (leak yo'q). Javob kutilayotgan taklif turganda — 409.
    """
    await _visible_candidate(db, company, offer_in.candidate_user_id)

    now = _now()
    calendar = WorkCalendar()
    offer = TalentOffer(
        company_id=company.id,
        candidate_user_id=offer_in.candidate_user_id,
        position_title=offer_in.position_title.strip(),
        message=offer_in.message.strip(),
        status=TalentOfferStatus.SENT,
        respond_due_at=calendar.add_work_minutes(now, RESPOND_WORKDAYS * calendar.minutes_per_day),
        created_at=now,
    )
    db.add(offer)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="An offer to this candidate is already awaiting a response")
    await db.refresh(offer)
    return offer


@router.post("/offers/{offer_id}/view", response_model=TalentOfferOut)
async def view_offer(offer_id: uuid.UUID, current_user: Candidate, db: AsyncSession = Depends(get_db)):
    offer = await _my_offer(db, offer_id, current_user)
    if offer.status == TalentOfferStatus.SENT:
        offer.status = TalentOfferStatus.VIEWED
    await db.commit()
    await db.refresh(offer)
    return offer


@router.post("/offers/{offer_id}/respond", response_model=TalentOfferOut)
async def respond_offer(offer_id: uuid.UUID, body: OfferRespond, current_user: Candidate, db: AsyncSession = Depends(get_db)):
    offer = await _my_offer(db, offer_id, current_user)
    if offer.status == TalentOfferStatus.RESPONDED:
        raise HTTPException(status_code=409, detail="Offer already answered")
    if body.hide_company and body.decision != OfferResponse.DECLINED:
        raise HTTPException(status_code=422, detail="Only a declined offer can hide the company")

    offer.status = TalentOfferStatus.RESPONDED
    offer.response = body.decision
    offer.response_note = (body.note or "").strip() or None
    offer.responded_at = _now()
    if body.hide_company:
        await _hide_company(db, current_user.id, offer.company_id)
    await db.commit()
    await db.refresh(offer)
    return offer
