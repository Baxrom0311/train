"""
Kandidat profili — tugallangan Run'lar natijasidan (CONTRACT.md §10.1, §33).

Profil har so'rovda hisoblanmaydi: `refresh_profiles` uni Run'lardan
hisoblab `talent_profiles` jadvaliga yozadi (Run yakunlanganda, sertifikat
bekor qilinganda, ssenariy katalog maydonlari o'zgarganda — §33.2), o'qish
`load_profiles` va `talent/search.py`dagi SQL orqali. Dvigatel jadvallarini
faqat o'qiydi.
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from statistics import fmean

from sqlalchemy import Select, delete, exists, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from app.models.credential import Certificate
from app.models.enums import RunStatus
from app.models.scenario import Run, Scenario, ScenarioVersion
from app.models.talent import TalentProfile

TOP_COMPETENCIES = 3
# pg_advisory_xact_lock(int, int) birinchi kaliti — boshqa qulflar bilan to'qnashmasin
LOCK_NAMESPACE = 0x7A1E
WRITE_BATCH = 1000


@dataclass(frozen=True)
class RunSummary:
    run_id: uuid.UUID
    scenario_id: uuid.UUID
    scenario_title: str
    company_name: str
    sector: str
    completed_at: datetime
    overall_score: float | None
    competency_scores: dict[str, float]
    strengths: list[str]

    def to_json(self) -> dict:
        return {
            "run_id": str(self.run_id),
            "scenario_id": str(self.scenario_id),
            "scenario_title": self.scenario_title,
            "company_name": self.company_name,
            "sector": self.sector,
            "completed_at": self.completed_at.isoformat(),
            "overall_score": self.overall_score,
            "competency_scores": self.competency_scores,
            "strengths": self.strengths,
        }

    @classmethod
    def from_json(cls, data: dict) -> RunSummary:
        return cls(
            run_id=uuid.UUID(data["run_id"]),
            scenario_id=uuid.UUID(data["scenario_id"]),
            scenario_title=data["scenario_title"],
            company_name=data["company_name"],
            sector=data["sector"],
            completed_at=datetime.fromisoformat(data["completed_at"]),
            overall_score=data["overall_score"],
            competency_scores=data["competency_scores"],
            strengths=data["strengths"],
        )


@dataclass
class Profile:
    """
    §10.1 profili. Bo'sh `Profile(user_id)` — profili yo'q nomzod (moslik hisobida).
    `runs` faqat `load_profiles(..., runs=True)`da to'ldiriladi; soni — `runs_completed`.
    """
    user_id: uuid.UUID
    overall_score: float | None = None
    competencies: dict[str, float] = field(default_factory=dict)
    sectors: list[str] = field(default_factory=list)
    last_completed_at: datetime | None = None
    runs_completed: int = 0
    runs: list[RunSummary] = field(default_factory=list)

    @classmethod
    def from_runs(cls, user_id: uuid.UUID, runs: list[RunSummary]) -> Profile:
        scores = [r.overall_score for r in runs if r.overall_score is not None]
        acc: dict[str, list[float]] = defaultdict(list)
        for r in runs:
            for key, value in r.competency_scores.items():
                acc[key].append(value)
        return cls(
            user_id=user_id,
            overall_score=round(fmean(scores), 1) if scores else None,
            competencies={k: round(fmean(v), 1) for k, v in sorted(acc.items())},
            sectors=sorted({r.sector for r in runs}),
            last_completed_at=max((r.completed_at for r in runs), default=None),
            runs_completed=len(runs),
            runs=sorted(runs, key=lambda r: r.completed_at, reverse=True),
        )

    @classmethod
    def from_row(cls, row: TalentProfile, *, runs: bool) -> Profile:
        return cls(
            user_id=row.user_id,
            overall_score=row.overall_score,
            # JSONB kalitlarni o'z tartibida saqlaydi — javobda kalit bo'yicha (§10.4)
            competencies=dict(sorted(row.competencies.items())),
            sectors=list(row.sectors),
            last_completed_at=row.last_completed_at,
            runs_completed=row.runs_completed,
            runs=[RunSummary.from_json(r) for r in row.runs] if runs else [],
        )

    @property
    def top_competencies(self) -> dict[str, float]:
        best = sorted(self.competencies.items(), key=lambda kv: -kv[1])[:TOP_COMPETENCIES]
        return dict(best)


# ---------------------------------------------------------------------------
# Hisoblash (Run'lardan) va yozish
# ---------------------------------------------------------------------------

def completed_runs(user_ids: Select | list[uuid.UUID]) -> Select:
    """Profilga kiradigan Run'lar (§10.1); talaba analitikasi ham shu filtrdan (§17.1)."""
    return (
        select(Run, Scenario)
        .join(ScenarioVersion, Run.scenario_version_id == ScenarioVersion.id)
        .join(Scenario, ScenarioVersion.scenario_id == Scenario.id)
        .where(
            Run.user_id.in_(user_ids),
            Run.status == RunStatus.COMPLETED,
            Run.final_report.is_not(None),
            # kompaniya sinovi natijasi faqat talaba va shu kompaniyaga (§26.1)
            Scenario.owner_company_id.is_(None),
            # jamoadagi hissa — to'liq shaxsiy natija emas (§29.4)
            Run.team_id.is_(None),
            # bekor qilingan sertifikatli ish profilga kirmaydi (§13.1)
            ~exists().where(Certificate.run_id == Run.id, Certificate.revoked_at.is_not(None)),
        )
    )


def _summary(run: Run, scenario: Scenario) -> RunSummary:
    report = run.final_report or {}
    ai = report.get("summary") or {}
    return RunSummary(
        run_id=run.id,
        scenario_id=scenario.id,
        scenario_title=scenario.title,
        company_name=scenario.company_name,
        sector=scenario.sector.value,
        completed_at=run.last_activity_at,
        overall_score=report.get("overall_score"),
        competency_scores=run.competency_scores or {},
        strengths=list(ai.get("strengths") or []),
    )


def _better(a: RunSummary, b: RunSummary) -> bool:
    """`a` `b`dan yaxshiroqmi: balli yuqori, teng bo'lsa — yangiroq."""
    return ((a.overall_score or -1), a.completed_at) > ((b.overall_score or -1), b.completed_at)


async def compute_profiles(db: AsyncSession, user_ids: Select | list[uuid.UUID]) -> dict[uuid.UUID, Profile]:
    """§10.1 hisobi Run'lardan; tugallangan Run'i yo'qlar natijaga kirmaydi. Faqat `refresh_profiles` uchun."""
    best: dict[tuple[uuid.UUID, uuid.UUID], RunSummary] = {}
    for run, scenario in (await db.execute(completed_runs(user_ids))).all():
        summary = _summary(run, scenario)
        key = (run.user_id, scenario.id)
        if key not in best or _better(summary, best[key]):
            best[key] = summary

    runs: dict[uuid.UUID, list[RunSummary]] = defaultdict(list)
    for (user_id, _), summary in best.items():
        runs[user_id].append(summary)
    return {user_id: Profile.from_runs(user_id, items) for user_id, items in runs.items()}


async def refresh_profiles(db: AsyncSession, user_ids: list[uuid.UUID]) -> None:
    """
    Foydalanuvchilar profilini qayta hisoblab `talent_profiles`ga yozadi (§33.2).
    Commit chaqiruvchida — profil uni o'zgartirgan yozuv bilan bitta tranzaksiyada.

    Har foydalanuvchiga tranzaksiya qulfi: ikki Run bir vaqtda yakunlansa,
    ikkinchisi birinchisi commit bo'lishini kutadi va ikkala Run'ni ham ko'radi.
    """
    ids = sorted(set(user_ids))
    if not ids:
        return
    await db.flush()
    for user_id in ids:   # tartiblangan — o'zaro kutib qolish (deadlock) bo'lmaydi
        await db.execute(select(func.pg_advisory_xact_lock(LOCK_NAMESPACE, func.hashtext(str(user_id)))))

    profiles = await compute_profiles(db, ids)
    gone = [i for i in ids if i not in profiles]
    if gone:
        await db.execute(delete(TalentProfile).where(TalentProfile.user_id.in_(gone)))
    if profiles:
        now = datetime.now(timezone.utc)
        rows = [
            {
                "user_id": p.user_id,
                "overall_score": p.overall_score,
                "runs_completed": p.runs_completed,
                "sectors": p.sectors,
                "competencies": p.competencies,
                "last_completed_at": p.last_completed_at,
                "runs": [r.to_json() for r in p.runs],
                "updated_at": now,
            }
            for p in profiles.values()
        ]
        for i in range(0, len(rows), WRITE_BATCH):   # asyncpg: ≤ 32767 parametr bitta so'rovda
            stmt = insert(TalentProfile).values(rows[i:i + WRITE_BATCH])
            await db.execute(stmt.on_conflict_do_update(
                index_elements=[TalentProfile.user_id],
                set_={k: stmt.excluded[k] for k in rows[0] if k != "user_id"},
            ))


async def refresh_scenario_profiles(db: AsyncSession, scenario_id: uuid.UUID) -> None:
    """Ssenariy katalog maydonlari (nom, kompaniya, soha) o'zgardi — uni o'tganlar profili (§33.2)."""
    user_ids = (await db.execute(
        select(Run.user_id)
        .join(ScenarioVersion, Run.scenario_version_id == ScenarioVersion.id)
        .where(ScenarioVersion.scenario_id == scenario_id, Run.status == RunStatus.COMPLETED)
        .distinct()
    )).scalars().all()
    await refresh_profiles(db, list(user_ids))


# ---------------------------------------------------------------------------
# O'qish
# ---------------------------------------------------------------------------

async def load_profiles(
    db: AsyncSession, user_ids: Select | list[uuid.UUID], *, runs: bool = True,
) -> dict[uuid.UUID, Profile]:
    """Saqlangan profillar; profili yo'q foydalanuvchi natijada yo'q. `runs=False` — Run ro'yxatisiz (yengil)."""
    # populate_existing: sessiyadagi eski nusxa emas — `refresh_profiles` yozgani
    q = select(TalentProfile).where(TalentProfile.user_id.in_(user_ids)).execution_options(populate_existing=True)
    if not runs:
        q = q.options(defer(TalentProfile.runs))
    return {row.user_id: Profile.from_row(row, runs=runs) for row in (await db.execute(q)).scalars()}


async def load_profile(db: AsyncSession, user_id: uuid.UUID, *, runs: bool = True) -> Profile | None:
    return (await load_profiles(db, [user_id], runs=runs)).get(user_id)
