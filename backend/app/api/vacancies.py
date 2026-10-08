"""
Kompaniya vakansiyalari — CONTRACT.md §23 (Modul 4).

Kompaniya (`manage_vacancies` + tasdiqlangan kompaniya): vakansiyalar, mos
nomzodlar (faqat §10 bo'yicha ko'rinadiganlar), arizalar. Talaba
(`receive_offers`): ochiq vakansiyalar, o'z mosligi, ariza.

Ariza — rozilik: ariza bergan talaba shu vakansiya egasiga ko'rinmasa ham
ariza ro'yxatida chiqadi; email baribir faqat taklif qabul qilinganda (§10.2).

Suhbat bosqichlari (§25): kompaniya arizachiga 1–3 vaqt taklif qiladi, talaba
birini tanlaydi yoki rad etadi, kompaniya natijani belgilaydi. Qulflash
tartibi — avval ariza, keyin suhbat.
"""
import uuid
from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.talent_hunt import CandidateCard, candidate_card, company_of, visible_profiles
from app.core.deps import require_permission
from app.database import get_db
from app.models.billing import Company
from app.models.enums import (
    ApplicationInterviewFormat, ApplicationInterviewOutcome, ApplicationInterviewStatus, ApplicationStatus,
    Competency, Employment, Sector, VacancyStatus, WorkFormat,
)
from app.models.talent import ApplicationInterview, Vacancy, VacancyApplication
from app.models.user import User
from app.notifications import meetings as meeting_events
from app.notifications.vacancies import application_received, application_rejected
from app.talent import meetings
from app.talent import vacancies as matching
from app.talent.profile import Profile, build_profiles

router = APIRouter(prefix="/api/v1/vacancies", tags=["Vacancies"])
org_router = APIRouter(prefix="/api/v1/company/vacancies", tags=["Vacancies - Company"])
users_router = APIRouter(prefix="/api/v1/users", tags=["Vacancies"])

MAX_OPEN = 20
MAX_REQUIREMENTS = 6
MAX_SCENARIOS = 5
SALARY_MAX = 1_000_000_000
# kompaniya ko'radigan arizalar; withdrawn — talaba rozilikni qaytarib oldi
VISIBLE_APPLICATIONS = (
    ApplicationStatus.APPLIED, ApplicationStatus.INTERVIEWING, ApplicationStatus.OFFERED, ApplicationStatus.REJECTED,
)
# hali hal qilinmagan ariza: taklif, rad etish, suhbat va qaytarib olish mumkin (§25.2)
PENDING_APPLICATIONS = (ApplicationStatus.APPLIED, ApplicationStatus.INTERVIEWING)
UPCOMING_LIMIT = 100


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Schemalar
# ---------------------------------------------------------------------------

class VacancyIn(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=20, max_length=4000)
    sector: Sector
    employment: Employment
    work_format: WorkFormat
    location: str | None = Field(default=None, max_length=120)
    salary_min: int | None = Field(default=None, ge=0, le=SALARY_MAX)
    salary_max: int | None = Field(default=None, ge=0, le=SALARY_MAX)
    requirements: dict[Competency, int] = Field(default_factory=dict, max_length=MAX_REQUIREMENTS)
    min_score: int | None = Field(default=None, ge=0, le=100)
    scenario_ids: list[uuid.UUID] = Field(default_factory=list, max_length=MAX_SCENARIOS)

    @field_validator("title", "description")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("too short")
        return v

    @field_validator("location")
    @classmethod
    def _location(cls, v: str | None) -> str | None:
        return (v or "").strip() or None

    @field_validator("requirements")
    @classmethod
    def _scores(cls, v: dict[Competency, int]) -> dict[Competency, int]:
        if any(not 0 <= score <= 100 for score in v.values()):
            raise ValueError("requirement score must be within 0..100")
        return v

    @field_validator("scenario_ids")
    @classmethod
    def _unique(cls, v: list[uuid.UUID]) -> list[uuid.UUID]:
        return list(dict.fromkeys(v))

    @model_validator(mode="after")
    def _salary(self):
        if self.salary_min is not None and self.salary_max is not None and self.salary_min > self.salary_max:
            raise ValueError("salary_min must not exceed salary_max")
        return self


class VacancyCreate(VacancyIn):
    status: Literal["draft", "open"] = "draft"


class VacancyStatusIn(BaseModel):
    status: Literal["open", "closed"]


class VacancyOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    title: str
    description: str
    sector: Sector
    employment: Employment
    work_format: WorkFormat
    location: str | None
    salary_min: int | None
    salary_max: int | None
    requirements: dict[str, int]
    min_score: int | None
    scenario_ids: list[uuid.UUID]
    status: VacancyStatus
    published_at: datetime | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VacancyCounts(BaseModel):
    applications: int
    new: int
    matches: int


class CompanyVacancyOut(VacancyOut):
    counts: VacancyCounts


class GapOut(BaseModel):
    competency: str
    required: int
    actual: float | None


class FitOut(BaseModel):
    fit: float
    meets: bool
    gaps: list[GapOut]
    sector_match: bool


class MatchOut(CandidateCard):
    fit: FitOut
    applied: bool


class InterviewProposeIn(BaseModel):
    slots: list[datetime] = Field(min_length=1, max_length=meetings.MAX_SLOTS)
    duration_minutes: int = Field(ge=15, le=120)
    format: ApplicationInterviewFormat
    place: str = Field(min_length=2, max_length=300)
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("slots")
    @classmethod
    def _slots(cls, v: list[datetime]) -> list[datetime]:
        slots = sorted(meetings.normalize_slot(s) for s in v)
        if len(set(slots)) != len(slots):
            raise ValueError("slots must be distinct")
        return slots

    @field_validator("place")
    @classmethod
    def _place(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("too short")
        return v

    @field_validator("note")
    @classmethod
    def _note(cls, v: str | None) -> str | None:
        return (v or "").strip() or None


class InterviewOutcomeIn(BaseModel):
    outcome: ApplicationInterviewOutcome
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("note")
    @classmethod
    def _note(cls, v: str | None) -> str | None:
        return (v or "").strip() or None


class InterviewConfirmIn(BaseModel):
    starts_at: datetime

    @field_validator("starts_at")
    @classmethod
    def _aware(cls, v: datetime) -> datetime:
        return meetings.normalize_slot(v)


class InterviewDeclineIn(BaseModel):
    reason: str | None = Field(default=None, max_length=500)

    @field_validator("reason")
    @classmethod
    def _reason(cls, v: str | None) -> str | None:
        return (v or "").strip() or None


class MyInterviewOut(BaseModel):
    """Talabaga: kompaniyaning ichki izohi (`outcome_note`) va muallifisiz (§25.4)."""
    id: uuid.UUID
    application_id: uuid.UUID
    round: int
    slots: list[datetime]
    duration_minutes: int
    format: ApplicationInterviewFormat
    place: str
    note: str | None
    status: ApplicationInterviewStatus
    starts_at: datetime | None
    confirmed_at: datetime | None
    decline_reason: str | None
    outcome: ApplicationInterviewOutcome | None
    expired: bool
    created_at: datetime
    updated_at: datetime


class InterviewOut(MyInterviewOut):
    outcome_note: str | None
    created_by: uuid.UUID | None


class UpcomingInterviewOut(InterviewOut):
    vacancy_id: uuid.UUID
    vacancy_title: str
    candidate_id: uuid.UUID
    candidate_name: str


class CompanyApplicationOut(BaseModel):
    id: uuid.UUID
    status: ApplicationStatus
    note: str | None
    created_at: datetime
    updated_at: datetime
    candidate: CandidateCard
    fit: FitOut
    interviews: list[InterviewOut]


class CompanyBrief(BaseModel):
    id: uuid.UUID
    name: str
    industry: str


class VacancyCard(VacancyOut):
    company: CompanyBrief
    my_fit: FitOut | None
    application_status: ApplicationStatus | None


class PracticeOut(BaseModel):
    scenario_id: uuid.UUID
    title: str
    sector: str
    company_name: str
    duration_days: int
    difficulty: str
    completed: bool
    practices: dict[str, int]


class VacancyDetail(VacancyCard):
    my_overall: float | None
    my_competencies: dict[str, float]
    practice: list[PracticeOut]
    interviews: list[MyInterviewOut]


class ApplyIn(BaseModel):
    note: str | None = Field(default=None, max_length=1000)


class ApplicationOut(BaseModel):
    id: uuid.UUID
    vacancy_id: uuid.UUID
    status: ApplicationStatus
    note: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MyApplicationOut(ApplicationOut):
    vacancy_title: str
    vacancy_status: VacancyStatus
    company_name: str
    sector: Sector
    interview: MyInterviewOut | None


# ---------------------------------------------------------------------------
# Yordamchilar
# ---------------------------------------------------------------------------

async def vacancy_company(
    current_user: Annotated[User, Depends(require_permission("manage_vacancies"))],
    db: AsyncSession = Depends(get_db),
) -> tuple[User, Company]:
    return current_user, await company_of(db, current_user)


Staff = Annotated[tuple[User, Company], Depends(vacancy_company)]
Candidate = Annotated[User, Depends(require_permission("receive_offers"))]


def _fit_out(f: matching.Fit) -> FitOut:
    return FitOut(
        fit=f.fit, meets=f.meets, sector_match=f.sector_match,
        gaps=[GapOut(competency=g.competency, required=g.required, actual=g.actual) for g in f.gaps],
    )


async def _own_vacancy(db: AsyncSession, company: Company, vacancy_id: uuid.UUID, *, lock: bool = False) -> Vacancy:
    q = select(Vacancy).where(Vacancy.id == vacancy_id)
    if lock:
        q = q.with_for_update()
    vacancy = (await db.execute(q)).scalars().first()
    if vacancy is None or vacancy.company_id != company.id:     # boshqa kompaniyaniki — "yo'q"
        raise HTTPException(status_code=404, detail="Vacancy not found")
    return vacancy


def _my_interview_out(interview: ApplicationInterview, now: datetime) -> MyInterviewOut:
    return MyInterviewOut(
        id=interview.id, application_id=interview.application_id, round=interview.round,
        slots=meetings.slot_times(interview), duration_minutes=interview.duration_minutes,
        format=interview.format, place=interview.place, note=interview.note, status=interview.status,
        starts_at=interview.starts_at, confirmed_at=interview.confirmed_at, decline_reason=interview.decline_reason,
        outcome=interview.outcome, expired=meetings.is_expired(interview, now),
        created_at=interview.created_at, updated_at=interview.updated_at,
    )


def _interview_out(interview: ApplicationInterview, now: datetime) -> InterviewOut:
    return InterviewOut(
        **_my_interview_out(interview, now).model_dump(),
        outcome_note=interview.outcome_note, created_by=interview.created_by,
    )


async def _company_application(
    db: AsyncSession, company: Company, vacancy_id: uuid.UUID, application_id: uuid.UUID,
) -> tuple[Vacancy, VacancyApplication]:
    """Kompaniyaning o'z vakansiyasidagi ariza, qulflangan; qaytarib olingani — "yo'q"."""
    vacancy = await _own_vacancy(db, company, vacancy_id)
    application = (await db.execute(
        select(VacancyApplication)
        .where(VacancyApplication.id == application_id, VacancyApplication.vacancy_id == vacancy.id)
        .with_for_update()
    )).scalars().first()
    if application is None or application.status == ApplicationStatus.WITHDRAWN:
        raise HTTPException(status_code=404, detail="Application not found")
    return vacancy, application


async def _application_interview(
    db: AsyncSession, application: VacancyApplication, interview_id: uuid.UUID,
) -> ApplicationInterview:
    interview = (await db.execute(
        select(ApplicationInterview)
        .where(ApplicationInterview.id == interview_id, ApplicationInterview.application_id == application.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )).scalars().first()
    if interview is None:
        raise HTTPException(status_code=404, detail="Interview not found")
    return interview


async def _check_scenarios(db: AsyncSession, ids: list[uuid.UUID]) -> None:
    if not ids:
        return
    known = await matching.published_scenarios(db)
    unknown = [str(i) for i in ids if i not in known]
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown or unpublished scenarios: {', '.join(unknown)}")


def _apply_fields(vacancy: Vacancy, body: VacancyIn) -> None:
    for name in ("title", "description", "sector", "employment", "work_format", "location",
                 "salary_min", "salary_max", "min_score"):
        setattr(vacancy, name, getattr(body, name))
    vacancy.requirements = {k.value: v for k, v in body.requirements.items()}
    vacancy.scenario_ids = [str(i) for i in body.scenario_ids]


async def _ensure_open_slot(db: AsyncSession, company: Company) -> None:
    """Bir vaqtda ≤ 20 ochiq vakansiya; kompaniya qatori qulflanadi — parallel ochishda ham limit buzilmaydi."""
    await db.execute(select(Company.id).where(Company.id == company.id).with_for_update())
    opened = await db.scalar(
        select(func.count()).select_from(Vacancy)
        .where(Vacancy.company_id == company.id, Vacancy.status == VacancyStatus.OPEN)
    )
    if opened >= MAX_OPEN:
        raise HTTPException(status_code=409, detail=f"A company can have at most {MAX_OPEN} open vacancies")


def _open(vacancy: Vacancy, now: datetime) -> None:
    vacancy.status = VacancyStatus.OPEN
    vacancy.published_at = vacancy.published_at or now
    vacancy.closed_at = None


async def _application_counts(db: AsyncSession, vacancy_ids: list[uuid.UUID]) -> dict[uuid.UUID, tuple[int, int]]:
    rows = (await db.execute(
        select(VacancyApplication.vacancy_id, VacancyApplication.status, func.count())
        .where(VacancyApplication.vacancy_id.in_(vacancy_ids))
        .group_by(VacancyApplication.vacancy_id, VacancyApplication.status)
    )).all()
    out: dict[uuid.UUID, tuple[int, int]] = {}
    for vacancy_id, state, n in rows:
        total, new = out.get(vacancy_id, (0, 0))
        if state in (ApplicationStatus.APPLIED, ApplicationStatus.INTERVIEWING, ApplicationStatus.OFFERED):
            total += n
        if state == ApplicationStatus.APPLIED:
            new += n
        out[vacancy_id] = (total, new)
    return out


async def _with_counts(db: AsyncSession, company: Company, vacancies: list[Vacancy]) -> list[CompanyVacancyOut]:
    if not vacancies:
        return []
    counts = await _application_counts(db, [v.id for v in vacancies])
    _, profiles = await visible_profiles(db, company)
    out = []
    for v in vacancies:
        total, new = counts.get(v.id, (0, 0))
        matches = sum(1 for p in profiles if matching.fit(p, v).meets)
        out.append(CompanyVacancyOut(
            **VacancyOut.model_validate(v).model_dump(),
            counts=VacancyCounts(applications=total, new=new, matches=matches),
        ))
    return out


# ---------------------------------------------------------------------------
# Kompaniya
# ---------------------------------------------------------------------------

@org_router.get("", response_model=list[CompanyVacancyOut])
async def list_company_vacancies(staff: Staff, db: AsyncSession = Depends(get_db)):
    """Ochiqlari tepada, keyin qoralama va yopilganlar; har guruhda yangilari oldin."""
    _, company = staff
    order = {VacancyStatus.OPEN: 0, VacancyStatus.DRAFT: 1, VacancyStatus.CLOSED: 2}
    vacancies = list((await db.execute(
        select(Vacancy).where(Vacancy.company_id == company.id).order_by(Vacancy.updated_at.desc())
    )).scalars())
    vacancies.sort(key=lambda v: order[v.status])
    return await _with_counts(db, company, vacancies)


@org_router.post("", response_model=CompanyVacancyOut, status_code=status.HTTP_201_CREATED)
async def create_vacancy(body: VacancyCreate, staff: Staff, db: AsyncSession = Depends(get_db)):
    user, company = staff
    await _check_scenarios(db, body.scenario_ids)
    now = _now()
    vacancy = Vacancy(company_id=company.id, created_by=user.id, status=VacancyStatus.DRAFT, created_at=now, updated_at=now)
    _apply_fields(vacancy, body)
    if body.status == "open":
        await _ensure_open_slot(db, company)
        _open(vacancy, now)
    db.add(vacancy)
    await db.commit()
    await db.refresh(vacancy)
    return (await _with_counts(db, company, [vacancy]))[0]


@org_router.get("/interviews", response_model=list[UpcomingInterviewOut])
async def list_company_interviews(staff: Staff, db: AsyncSession = Depends(get_db)):
    """§25.4: faol (`proposed | confirmed`) suhbatlar, vaqti bo'yicha; boshlangan `confirmed` — natija kutmoqda."""
    _, company = staff
    rows = (await db.execute(
        select(ApplicationInterview, VacancyApplication, Vacancy, User)
        .join(VacancyApplication, VacancyApplication.id == ApplicationInterview.application_id)
        .join(Vacancy, Vacancy.id == VacancyApplication.vacancy_id)
        .join(User, User.id == VacancyApplication.user_id)
        .where(Vacancy.company_id == company.id, ApplicationInterview.status.in_(meetings.ACTIVE))
    )).all()
    rows = sorted(rows, key=lambda r: meetings.sort_key(r[0]))[:UPCOMING_LIMIT]
    now = _now()
    return [
        UpcomingInterviewOut(
            **_interview_out(interview, now).model_dump(),
            vacancy_id=vacancy.id, vacancy_title=vacancy.title, candidate_id=user.id, candidate_name=user.full_name,
        )
        for interview, _, vacancy, user in rows
    ]


@org_router.get("/{vacancy_id}", response_model=CompanyVacancyOut)
async def get_company_vacancy(vacancy_id: uuid.UUID, staff: Staff, db: AsyncSession = Depends(get_db)):
    _, company = staff
    return (await _with_counts(db, company, [await _own_vacancy(db, company, vacancy_id)]))[0]


@org_router.put("/{vacancy_id}", response_model=CompanyVacancyOut)
async def update_vacancy(vacancy_id: uuid.UUID, body: VacancyIn, staff: Staff, db: AsyncSession = Depends(get_db)):
    _, company = staff
    vacancy = await _own_vacancy(db, company, vacancy_id, lock=True)
    await _check_scenarios(db, body.scenario_ids)
    _apply_fields(vacancy, body)
    vacancy.updated_at = _now()
    await db.commit()
    await db.refresh(vacancy)
    return (await _with_counts(db, company, [vacancy]))[0]


@org_router.post("/{vacancy_id}/status", response_model=CompanyVacancyOut)
async def set_vacancy_status(vacancy_id: uuid.UUID, body: VacancyStatusIn, staff: Staff, db: AsyncSession = Depends(get_db)):
    """draft/closed → open (limit), open/draft → closed. Takror bir xil holat — o'zgarishsiz."""
    _, company = staff
    vacancy = await _own_vacancy(db, company, vacancy_id, lock=True)
    now = _now()
    if body.status == "open" and vacancy.status != VacancyStatus.OPEN:
        await _ensure_open_slot(db, company)
        _open(vacancy, now)
        vacancy.updated_at = now
    elif body.status == "closed" and vacancy.status != VacancyStatus.CLOSED:
        vacancy.status = VacancyStatus.CLOSED
        vacancy.closed_at = now
        vacancy.updated_at = now
    await db.commit()
    await db.refresh(vacancy)
    return (await _with_counts(db, company, [vacancy]))[0]


@org_router.get("/{vacancy_id}/matches", response_model=list[MatchOut])
async def get_matches(vacancy_id: uuid.UUID, staff: Staff, db: AsyncSession = Depends(get_db)):
    """§23.3: faqat ko'rinadigan nomzodlar, fit ≥ 50, ko'pi bilan 50 ta."""
    _, company = staff
    vacancy = await _own_vacancy(db, company, vacancy_id)
    users, profiles = await visible_profiles(db, company)
    applied = set((await db.execute(
        select(VacancyApplication.user_id).where(
            VacancyApplication.vacancy_id == vacancy.id, VacancyApplication.status != ApplicationStatus.WITHDRAWN,
        )
    )).scalars())
    scored = [(p, matching.fit(p, vacancy)) for p in profiles]
    scored = [(p, f) for p, f in scored if f.fit >= matching.MATCH_MIN_FIT]
    scored.sort(key=lambda pf: pf[1].sort_key(pf[0].overall_score), reverse=True)
    return [
        MatchOut(**candidate_card(users[p.user_id], p).model_dump(), fit=_fit_out(f), applied=p.user_id in applied)
        for p, f in scored[:matching.MAX_MATCHES]
    ]


@org_router.get("/{vacancy_id}/applications", response_model=list[CompanyApplicationOut])
async def get_applications(vacancy_id: uuid.UUID, staff: Staff, db: AsyncSession = Depends(get_db)):
    """Kutayotganlar tepada, keyin suhbatdagilar, taklif yuborilgan va rad etilganlar; har biri moslik bo'yicha."""
    _, company = staff
    vacancy = await _own_vacancy(db, company, vacancy_id)
    rows = (await db.execute(
        select(VacancyApplication, User)
        .join(User, User.id == VacancyApplication.user_id)
        .where(
            VacancyApplication.vacancy_id == vacancy.id,
            VacancyApplication.status.in_(VISIBLE_APPLICATIONS),
            User.is_active.is_(True),
        )
    )).all()
    profiles = await build_profiles(db, [user.id for _, user in rows]) if rows else {}
    interviews = await meetings.history(db, [application.id for application, _ in rows])
    order = {
        ApplicationStatus.APPLIED: 0, ApplicationStatus.INTERVIEWING: 1,
        ApplicationStatus.OFFERED: 2, ApplicationStatus.REJECTED: 3,
    }
    now = _now()
    out = []
    for application, user in rows:
        # profil yo'qolishi mumkin (sertifikat bekor qilingan) — bo'sh profil bilan ko'rsatiladi
        p = profiles.get(user.id) or Profile(user.id)
        f = matching.fit(p, vacancy)
        out.append((order[application.status], -f.fit, CompanyApplicationOut(
            id=application.id, status=application.status, note=application.note,
            created_at=application.created_at, updated_at=application.updated_at,
            candidate=candidate_card(user, p), fit=_fit_out(f),
            interviews=[_interview_out(i, now) for i in interviews[application.id]],
        )))
    out.sort(key=lambda x: (x[0], x[1], x[2].created_at))
    return [x[2] for x in out]


@org_router.post("/{vacancy_id}/applications/{application_id}/reject", response_model=ApplicationOut)
async def reject_application(vacancy_id: uuid.UUID, application_id: uuid.UUID, staff: Staff, db: AsyncSession = Depends(get_db)):
    _, company = staff
    vacancy, application = await _company_application(db, company, vacancy_id, application_id)
    if application.status not in PENDING_APPLICATIONS:
        raise HTTPException(status_code=409, detail="Only a pending application can be rejected")
    now = _now()
    application.status = ApplicationStatus.REJECTED
    application.updated_at = now
    await meetings.close_active(db, application.id, now)        # §25.2: rad xabari yetarli
    await application_rejected(db, application, vacancy, company.name, now)    # §23.7
    await db.commit()
    await db.refresh(application)
    return application


@org_router.post(
    "/{vacancy_id}/applications/{application_id}/interviews",
    response_model=InterviewOut, status_code=status.HTTP_201_CREATED,
)
async def propose_interview(
    vacancy_id: uuid.UUID, application_id: uuid.UUID, body: InterviewProposeIn, staff: Staff,
    db: AsyncSession = Depends(get_db),
):
    """§25.2: `applied | interviewing` arizaga, faol suhbat yo'q bo'lsa; ariza → `interviewing`."""
    user, company = staff
    vacancy, application = await _company_application(db, company, vacancy_id, application_id)
    if application.status not in PENDING_APPLICATIONS:
        raise HTTPException(status_code=409, detail="Only a pending application can be invited to an interview")
    now = _now()
    problem = meetings.slot_problem(body.slots, now)
    if problem:
        raise HTTPException(status_code=422, detail=problem)
    if await meetings.active(db, application.id) is not None:
        raise HTTPException(status_code=409, detail="This application already has an active interview")
    interview = ApplicationInterview(
        application_id=application.id, created_by=user.id, round=await meetings.next_round(db, application.id),
        slots=[slot.isoformat() for slot in body.slots], duration_minutes=body.duration_minutes,
        format=body.format, place=body.place, note=body.note, status=ApplicationInterviewStatus.PROPOSED,
        created_at=now, updated_at=now,
    )
    db.add(interview)
    application.status = ApplicationStatus.INTERVIEWING
    application.updated_at = now
    try:
        await db.flush()
        await meeting_events.proposed(db, interview, application, vacancy, company.name, now)
        await db.commit()
    except IntegrityError:      # ariza qulflangan — amalda faqat himoya
        await db.rollback()
        raise HTTPException(status_code=409, detail="This application already has an active interview")
    return _interview_out(interview, now)


@org_router.post(
    "/{vacancy_id}/applications/{application_id}/interviews/{interview_id}/cancel", response_model=InterviewOut,
)
async def cancel_interview(
    vacancy_id: uuid.UUID, application_id: uuid.UUID, interview_id: uuid.UUID, staff: Staff,
    db: AsyncSession = Depends(get_db),
):
    _, company = staff
    vacancy, application = await _company_application(db, company, vacancy_id, application_id)
    interview = await _application_interview(db, application, interview_id)
    if interview.status not in meetings.ACTIVE:
        raise HTTPException(status_code=409, detail="Only an active interview can be cancelled")
    now = _now()
    interview.status = ApplicationInterviewStatus.CANCELLED
    interview.updated_at = now
    await meeting_events.cancelled(db, interview, application, vacancy, company.name, now)
    await db.commit()
    return _interview_out(interview, now)


@org_router.post(
    "/{vacancy_id}/applications/{application_id}/interviews/{interview_id}/outcome", response_model=InterviewOut,
)
async def record_interview_outcome(
    vacancy_id: uuid.UUID, application_id: uuid.UUID, interview_id: uuid.UUID, body: InterviewOutcomeIn,
    staff: Staff, db: AsyncSession = Depends(get_db),
):
    """§25.2: faqat `confirmed` va boshlangan suhbat; o'tmadi/kelmadi — ariza rad etiladi."""
    _, company = staff
    vacancy, application = await _company_application(db, company, vacancy_id, application_id)
    interview = await _application_interview(db, application, interview_id)
    now = _now()
    if interview.status != ApplicationInterviewStatus.CONFIRMED:
        raise HTTPException(status_code=409, detail="Only a confirmed interview can be completed")
    if now < interview.starts_at:
        raise HTTPException(status_code=409, detail="The interview has not started yet")
    interview.status = ApplicationInterviewStatus.COMPLETED
    interview.outcome = body.outcome
    interview.outcome_note = body.note
    interview.updated_at = now
    if body.outcome != ApplicationInterviewOutcome.PASSED:
        application.status = ApplicationStatus.REJECTED
        application.updated_at = now
        await application_rejected(db, application, vacancy, company.name, now)    # §23.7
    await db.commit()
    return _interview_out(interview, now)


# ---------------------------------------------------------------------------
# Talaba
# ---------------------------------------------------------------------------

def _vacancy_card(vacancy: Vacancy, company: Company, profile: Profile | None, application: VacancyApplication | None) -> dict:
    return {
        **VacancyOut.model_validate(vacancy).model_dump(),
        "company": CompanyBrief(id=company.id, name=company.name, industry=company.industry),
        "my_fit": _fit_out(matching.fit(profile, vacancy)) if profile else None,
        "application_status": application.status if application else None,
    }


async def _my_applications(db: AsyncSession, user_id: uuid.UUID) -> dict[uuid.UUID, VacancyApplication]:
    rows = (await db.execute(select(VacancyApplication).where(VacancyApplication.user_id == user_id))).scalars()
    return {a.vacancy_id: a for a in rows}


async def _student_vacancy(db: AsyncSession, user: User, vacancy_id: uuid.UUID, *, lock: bool = False) -> tuple[Vacancy, Company]:
    found = await matching.student_vacancy(db, user.id, vacancy_id, lock=lock)
    if found is None:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    return found


@router.get("", response_model=list[VacancyCard])
async def list_vacancies(current_user: Candidate, db: AsyncSession = Depends(get_db), sector: Sector | None = None):
    """Ochiq vakansiyalar: mosligi yuqorilari tepada (profil yo'q bo'lsa — yangilari)."""
    q = matching.student_visible().where(Vacancy.status == VacancyStatus.OPEN)
    if sector is not None:
        q = q.where(Vacancy.sector == sector)
    rows = (await db.execute(q)).all()
    profile = (await build_profiles(db, [current_user.id])).get(current_user.id)
    mine = await _my_applications(db, current_user.id)
    cards = [VacancyCard(**_vacancy_card(v, c, profile, mine.get(v.id))) for v, c in rows]
    cards.sort(key=lambda c: (c.my_fit.fit if c.my_fit else -1, c.published_at or c.created_at), reverse=True)
    return cards


@router.get("/{vacancy_id}", response_model=VacancyDetail)
async def get_vacancy(vacancy_id: uuid.UUID, current_user: Candidate, db: AsyncSession = Depends(get_db)):
    vacancy, company = await _student_vacancy(db, current_user, vacancy_id)
    profile = (await build_profiles(db, [current_user.id])).get(current_user.id)
    application = (await _my_applications(db, current_user.id)).get(vacancy.id)
    # profil yo'q — hamma talab "yetishmaydi", mashq ro'yxati shundan
    gaps = matching.fit(profile or Profile(current_user.id), vacancy).gaps
    completed = {r.scenario_id for r in profile.runs} if profile else set()
    practice = matching.practice(vacancy, gaps, await matching.published_scenarios(db), completed)
    interviews = (await meetings.history(db, [application.id]))[application.id] if application else []
    now = _now()
    return VacancyDetail(
        **_vacancy_card(vacancy, company, profile, application),
        my_overall=profile.overall_score if profile else None,
        my_competencies=profile.competencies if profile else {},
        practice=[
            PracticeOut(
                scenario_id=o.scenario_id, title=o.title, sector=o.sector, company_name=o.company_name,
                duration_days=o.duration_days, difficulty=o.difficulty, completed=done, practices=practices,
            )
            for o, done, practices in practice
        ],
        interviews=[_my_interview_out(i, now) for i in interviews],
    )


@router.post("/{vacancy_id}/apply", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
async def apply(vacancy_id: uuid.UUID, body: ApplyIn, current_user: Candidate, db: AsyncSession = Depends(get_db)):
    vacancy, _ = await _student_vacancy(db, current_user, vacancy_id, lock=True)
    if vacancy.status != VacancyStatus.OPEN:
        raise HTTPException(status_code=409, detail="Vacancy is closed")
    if current_user.id not in await build_profiles(db, [current_user.id]):
        raise HTTPException(status_code=422, detail="Complete at least one scenario before applying")

    now = _now()
    note = (body.note or "").strip() or None
    application = (await db.execute(
        select(VacancyApplication)
        .where(VacancyApplication.vacancy_id == vacancy.id, VacancyApplication.user_id == current_user.id)
        .with_for_update()
    )).scalars().first()
    if application is None:
        application = VacancyApplication(
            vacancy_id=vacancy.id, user_id=current_user.id, note=note,
            status=ApplicationStatus.APPLIED, created_at=now, updated_at=now,
        )
        db.add(application)
        await db.flush()
    elif application.status == ApplicationStatus.WITHDRAWN:
        application.status = ApplicationStatus.APPLIED
        application.note = note
        application.updated_at = now
    else:
        raise HTTPException(status_code=409, detail="Already applied")
    # dedupe — qayta ariza (withdrawn → applied) kompaniyaga qayta xabar bermaydi
    await application_received(db, application, vacancy, current_user.full_name, now)
    await db.commit()
    await db.refresh(application)
    return application


async def _my_application(db: AsyncSession, user: User, vacancy_id: uuid.UUID) -> VacancyApplication:
    application = (await db.execute(
        select(VacancyApplication)
        .where(VacancyApplication.vacancy_id == vacancy_id, VacancyApplication.user_id == user.id)
        .with_for_update()
    )).scalars().first()
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


@router.post("/{vacancy_id}/withdraw", response_model=ApplicationOut)
async def withdraw(vacancy_id: uuid.UUID, current_user: Candidate, db: AsyncSession = Depends(get_db)):
    application = await _my_application(db, current_user, vacancy_id)
    if application.status not in PENDING_APPLICATIONS:
        raise HTTPException(status_code=409, detail="Only a pending application can be withdrawn")
    now = _now()
    application.status = ApplicationStatus.WITHDRAWN
    application.updated_at = now
    closed = await meetings.close_active(db, application.id, now)
    if closed is not None:      # §25.2: kompaniya rejalashtirgan suhbatdan xabar topsin
        vacancy = await db.get(Vacancy, vacancy_id)
        await meeting_events.declined(db, closed, vacancy, current_user.full_name, now, withdrawn=True)
    await db.commit()
    await db.refresh(application)
    return application


async def _my_interview(
    db: AsyncSession, user: User, vacancy_id: uuid.UUID, interview_id: uuid.UUID,
) -> tuple[Vacancy, ApplicationInterview]:
    """O'z arizasi (qaytarib olinmagan) suhbati; boshqasi — 404 (§25.3)."""
    application = await _my_application(db, user, vacancy_id)
    if application.status == ApplicationStatus.WITHDRAWN:
        raise HTTPException(status_code=404, detail="Interview not found")
    interview = await _application_interview(db, application, interview_id)
    return await db.get(Vacancy, vacancy_id), interview


@router.post("/{vacancy_id}/interviews/{interview_id}/confirm", response_model=MyInterviewOut)
async def confirm_interview(
    vacancy_id: uuid.UUID, interview_id: uuid.UUID, body: InterviewConfirmIn, current_user: Candidate,
    db: AsyncSession = Depends(get_db),
):
    """§25.2: taklif qilingan variantlardan biri va hali kelmagan bo'lsa."""
    vacancy, interview = await _my_interview(db, current_user, vacancy_id, interview_id)
    now = _now()
    if interview.status != ApplicationInterviewStatus.PROPOSED:
        raise HTTPException(status_code=409, detail="Only a proposed interview can be confirmed")
    if body.starts_at not in meetings.slot_times(interview):
        raise HTTPException(status_code=409, detail="Pick one of the proposed times")
    if body.starts_at <= now:
        raise HTTPException(status_code=409, detail="This time has already passed")
    interview.status = ApplicationInterviewStatus.CONFIRMED
    interview.starts_at = body.starts_at
    interview.confirmed_at = now
    interview.updated_at = now
    await meeting_events.confirmed(db, interview, vacancy, current_user.full_name, now)
    await db.commit()
    return _my_interview_out(interview, now)


@router.post("/{vacancy_id}/interviews/{interview_id}/decline", response_model=MyInterviewOut)
async def decline_interview(
    vacancy_id: uuid.UUID, interview_id: uuid.UUID, body: InterviewDeclineIn, current_user: Candidate,
    db: AsyncSession = Depends(get_db),
):
    vacancy, interview = await _my_interview(db, current_user, vacancy_id, interview_id)
    if interview.status not in meetings.ACTIVE:
        raise HTTPException(status_code=409, detail="Only an active interview can be declined")
    now = _now()
    interview.status = ApplicationInterviewStatus.DECLINED
    interview.decline_reason = body.reason
    interview.updated_at = now
    await meeting_events.declined(db, interview, vacancy, current_user.full_name, now)
    await db.commit()
    return _my_interview_out(interview, now)


@users_router.get("/me/applications", response_model=list[MyApplicationOut])
async def my_applications(current_user: Candidate, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(VacancyApplication, Vacancy, Company)
        .join(Vacancy, Vacancy.id == VacancyApplication.vacancy_id)
        .join(Company, Company.id == Vacancy.company_id)
        .where(VacancyApplication.user_id == current_user.id)
        .order_by(VacancyApplication.created_at.desc())
    )).all()
    active = {
        i.application_id: i for i in (await db.execute(
            select(ApplicationInterview).where(
                ApplicationInterview.application_id.in_([a.id for a, _, _ in rows]),
                ApplicationInterview.status.in_(meetings.ACTIVE),
            )
        )).scalars()
    } if rows else {}
    now = _now()
    return [
        MyApplicationOut(
            **ApplicationOut.model_validate(a).model_dump(),
            vacancy_title=v.title, vacancy_status=v.status, company_name=c.name, sector=v.sector,
            interview=_my_interview_out(active[a.id], now) if a.id in active else None,
        )
        for a, v, c in rows
    ]
