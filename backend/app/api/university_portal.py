"""
Universitet portali — talabalarning ssenariy dvigateli natijalari (CONTRACT.md §12).
Modul 6 egaligi: backend/app/api/university_portal.py.

Profil §10.1 bilan bir xil hisoblanadi (`build_profiles`); javoblar, chat va
fayllar universitetga ko'rsatilmaydi. `candidate_visibility` bu yerga
ta'sir qilmaydi — u faqat kompaniyalar uchun.
"""
import uuid
from collections import defaultdict
from datetime import datetime
from enum import Enum
from statistics import fmean
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_permission
from app.database import get_db
from app.models.billing import University
from app.models.enums import OrgType, RunStatus, Sector
from app.models.scenario import Run, Scenario, ScenarioVersion
from app.models.user import User
from app.talent.profile import Profile, RunSummary, build_profiles

router = APIRouter(prefix="/api/v1/university", tags=["University Portal"])
users_router = APIRouter(prefix="/api/v1/users", tags=["University Portal - Affiliation"])

IN_PROGRESS = (RunStatus.SCHEDULED, RunStatus.ACTIVE)
TOP_STUDENTS = 5


# ---------------------------------------------------------------------------
# Schemalar
# ---------------------------------------------------------------------------

class UniversityOut(BaseModel):
    id: uuid.UUID
    name: str
    city: str

    model_config = ConfigDict(from_attributes=True)


class StudentRow(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str
    joined_at: datetime | None
    overall_score: float | None
    runs_completed: int
    runs_in_progress: int
    sectors: list[str]
    top_competencies: dict[str, float]
    last_completed_at: datetime | None


class RunSummaryOut(BaseModel):
    scenario_title: str
    company_name: str
    sector: str
    completed_at: datetime
    overall_score: float | None
    competency_scores: dict[str, float]
    strengths: list[str]


class InProgressRun(BaseModel):
    scenario_title: str
    sector: str
    status: RunStatus
    ends_at: datetime


class StudentDetail(StudentRow):
    competencies: dict[str, float]
    runs: list[RunSummaryOut]
    in_progress: list[InProgressRun]


class StudentPage(BaseModel):
    items: list[StudentRow]
    total: int


class SectorStat(BaseModel):
    sector: str
    students: int
    avg_score: float | None


class Overview(BaseModel):
    university: UniversityOut
    students_total: int
    students_with_results: int
    runs_completed: int
    runs_in_progress: int
    avg_score: float | None
    sectors: list[SectorStat]
    competencies: dict[str, float]
    top_students: list[StudentRow]


class AffiliationUpdate(BaseModel):
    university_id: uuid.UUID | None


class AffiliationOut(BaseModel):
    university: UniversityOut | None


class SortBy(str, Enum):
    SCORE = "score"
    RECENT = "recent"
    NAME = "name"


# ---------------------------------------------------------------------------
# Yordamchilar
# ---------------------------------------------------------------------------

async def verified_university(
    current_user: Annotated[User, Depends(require_permission("manage_universities"))],
    db: AsyncSession = Depends(get_db),
) -> University:
    """`manage_universities` + foydalanuvchi tasdiqlangan universitetga tegishli (§12.1)."""
    if current_user.org_type != OrgType.UNIVERSITY or not current_user.org_id:
        raise HTTPException(status_code=403, detail="Only university staff can access the portal")
    university = await db.get(University, current_user.org_id)
    if not university or not university.is_verified:
        raise HTTPException(status_code=403, detail="University is not verified")
    return university


VerifiedUniversity = Annotated[University, Depends(verified_university)]


def _students_of(university_id: uuid.UUID):
    """Universitet talabalari: bog'langan va tashkilot xodimi emas (§12.1)."""
    return select(User).where(User.university_id == university_id, User.org_id.is_(None))


async def _in_progress(db: AsyncSession, user_ids) -> dict[uuid.UUID, list[InProgressRun]]:
    rows = await db.execute(
        select(Run.user_id, Run.status, Run.ends_at, Scenario.title, Scenario.sector)
        .join(ScenarioVersion, Run.scenario_version_id == ScenarioVersion.id)
        .join(Scenario, ScenarioVersion.scenario_id == Scenario.id)
        .where(Run.user_id.in_(user_ids), Run.status.in_(IN_PROGRESS), Scenario.owner_company_id.is_(None))
        .order_by(Run.ends_at)
    )
    result: dict[uuid.UUID, list[InProgressRun]] = defaultdict(list)
    for row in rows:
        result[row.user_id].append(InProgressRun(
            scenario_title=row.title, sector=row.sector.value, status=row.status, ends_at=row.ends_at,
        ))
    return result


def _row(user: User, profile: Profile | None, active: list[InProgressRun]) -> StudentRow:
    return StudentRow(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        joined_at=user.created_at,
        overall_score=profile.overall_score if profile else None,
        runs_completed=len(profile.runs) if profile else 0,
        runs_in_progress=len(active),
        sectors=profile.sectors if profile else [],
        top_competencies=profile.top_competencies if profile else {},
        last_completed_at=profile.last_completed_at if profile else None,
    )


def _run_out(r: RunSummary) -> RunSummaryOut:
    return RunSummaryOut(
        scenario_title=r.scenario_title, company_name=r.company_name, sector=r.sector,
        completed_at=r.completed_at, overall_score=r.overall_score,
        competency_scores=r.competency_scores, strengths=r.strengths,
    )


def _avg(values) -> float | None:
    values = [v for v in values if v is not None]
    return round(fmean(values), 1) if values else None


async def _load(db: AsyncSession, university_id: uuid.UUID):
    """Talabalar, ularning profillari va ketayotgan ishlari."""
    students = list((await db.execute(_students_of(university_id))).scalars())
    if not students:
        return [], {}, {}
    ids = [s.id for s in students]
    return students, await build_profiles(db, ids), await _in_progress(db, ids)


def _sort_key(sort: SortBy):
    if sort == SortBy.NAME:
        return lambda r: r.full_name.casefold()
    if sort == SortBy.RECENT:
        # natijasi yo'qlar oxirida
        return lambda r: (r.last_completed_at is not None, r.last_completed_at or datetime.min)
    return lambda r: (r.overall_score is not None, r.overall_score or 0, r.runs_completed)


# ---------------------------------------------------------------------------
# Universitet xodimi
# ---------------------------------------------------------------------------

@router.get("/list", response_model=list[UniversityOut])
async def list_universities(db: AsyncSession = Depends(get_db)):
    """Tasdiqlangan universitetlar — ochiq: talaba ro'yxatdan o'tishda tanlaydi (§11.1)."""
    result = await db.execute(select(University).where(University.is_verified.is_(True)).order_by(University.name))
    return result.scalars().all()


@router.get("/overview", response_model=Overview)
async def get_overview(university: VerifiedUniversity, db: AsyncSession = Depends(get_db)):
    students, profiles, active = await _load(db, university.id)
    rows = [_row(s, profiles.get(s.id), active.get(s.id, [])) for s in students]

    by_sector: dict[str, dict[uuid.UUID, list[float]]] = defaultdict(lambda: defaultdict(list))
    by_competency: dict[str, list[float]] = defaultdict(list)
    for p in profiles.values():
        for r in p.runs:
            if r.overall_score is not None:
                by_sector[r.sector][p.user_id].append(r.overall_score)
            else:
                by_sector[r.sector].setdefault(p.user_id, [])
        for key, value in p.competencies.items():
            by_competency[key].append(value)

    sectors = [
        SectorStat(
            sector=sector,
            students=len(per_student),
            avg_score=_avg(score for scores in per_student.values() for score in scores),
        )
        for sector, per_student in by_sector.items()
    ]
    sectors.sort(key=lambda s: (-s.students, s.sector))

    ranked = sorted((r for r in rows if r.overall_score is not None), key=_sort_key(SortBy.SCORE), reverse=True)
    return Overview(
        university=UniversityOut.model_validate(university),
        students_total=len(students),
        students_with_results=len(profiles),
        runs_completed=sum(len(p.runs) for p in profiles.values()),
        runs_in_progress=sum(len(a) for a in active.values()),
        avg_score=_avg(p.overall_score for p in profiles.values()),
        sectors=sectors,
        competencies={k: round(fmean(v), 1) for k, v in sorted(by_competency.items())},
        top_students=ranked[:TOP_STUDENTS],
    )


@router.get("/students", response_model=StudentPage)
async def get_students(
    university: VerifiedUniversity,
    db: AsyncSession = Depends(get_db),
    q: str | None = Query(default=None, max_length=100),
    sector: Sector | None = None,
    has_results: bool | None = None,
    sort: SortBy = SortBy.SCORE,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    students, profiles, active = await _load(db, university.id)
    rows = [_row(s, profiles.get(s.id), active.get(s.id, [])) for s in students]
    needle = (q or "").strip().casefold()
    matched = [
        r for r in rows
        if (not needle or needle in r.full_name.casefold() or needle in r.email.casefold())
        and (sector is None or sector.value in r.sectors)
        and (has_results is None or (r.runs_completed > 0) == has_results)
    ]
    matched.sort(key=_sort_key(sort), reverse=sort != SortBy.NAME)
    return StudentPage(items=matched[offset:offset + limit], total=len(matched))


async def _own_student(db: AsyncSession, university_id: uuid.UUID, user_id: uuid.UUID) -> User:
    student = (await db.execute(_students_of(university_id).where(User.id == user_id))).scalars().first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.get("/students/{user_id}", response_model=StudentDetail)
async def get_student(user_id: uuid.UUID, university: VerifiedUniversity, db: AsyncSession = Depends(get_db)):
    student = await _own_student(db, university.id, user_id)
    profile = (await build_profiles(db, [student.id])).get(student.id)
    active = (await _in_progress(db, [student.id])).get(student.id, [])
    return StudentDetail(
        **_row(student, profile, active).model_dump(),
        competencies=profile.competencies if profile else {},
        runs=[_run_out(r) for r in profile.runs] if profile else [],
        in_progress=active,
    )


@router.delete("/students/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def detach_student(user_id: uuid.UUID, university: VerifiedUniversity, db: AsyncSession = Depends(get_db)):
    """Noto'g'ri bog'langan talabani ajratish; akkaunt va natijalar qoladi (§12.1)."""
    student = await _own_student(db, university.id, user_id)
    student.university_id = None
    await db.commit()


# ---------------------------------------------------------------------------
# Talaba: o'z universiteti
# ---------------------------------------------------------------------------

Student = Annotated[User, Depends(require_permission("join_university"))]


async def _affiliation(db: AsyncSession, user: User) -> AffiliationOut:
    university = await db.get(University, user.university_id) if user.university_id else None
    if university and not university.is_verified:
        university = None
    return AffiliationOut(university=UniversityOut.model_validate(university) if university else None)


@users_router.get("/me/university", response_model=AffiliationOut)
async def get_my_university(user: Student, db: AsyncSession = Depends(get_db)):
    return await _affiliation(db, user)


@users_router.patch("/me/university", response_model=AffiliationOut)
async def set_my_university(data: AffiliationUpdate, user: Student, db: AsyncSession = Depends(get_db)):
    if data.university_id is not None:
        university = await db.get(University, data.university_id)
        if not university or not university.is_verified:
            raise HTTPException(status_code=404, detail="University not found")
    user.university_id = data.university_id
    await db.commit()
    return await _affiliation(db, user)
