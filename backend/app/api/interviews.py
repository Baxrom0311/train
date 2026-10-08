"""
AI suhbat mashqi — CONTRACT.md §24 (Modul 14).

Talaba (`practice_interviews`) vakansiya bo'yicha sinov suhbatidan o'tadi.
Natija shaxsiy: faqat suhbat egasiga ko'rinadi, profil va moslikka ta'sir
qilmaydi. Oqim va AI — `app/interview/flow.py`.
"""
import uuid
from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import rate_limit, require_permission
from app.core.redis_client import get_arq_pool
from app.database import get_db
from app.interview import flow
from app.interview.jobs import enqueue_report
from app.models.enums import InterviewMessageKind, InterviewRole, InterviewStatus, Sector
from app.models.interview import Interview
from app.models.user import User

router = APIRouter(prefix="/api/v1/interviews", tags=["Interviews"])

LIST_LIMIT = 50

Student = Annotated[User, Depends(require_permission("practice_interviews"))]


def get_now() -> datetime:
    """Testlarda `dependency_overrides` bilan aniq vaqt beriladi."""
    return datetime.now(timezone.utc)


async def get_report_queue():
    return await get_arq_pool()


# ── Sxemalar ──────────────────────────────────────────────────────────


class InterviewStart(BaseModel):
    vacancy_id: uuid.UUID
    lang: Literal["uz", "ru", "en"] = "uz"


class AnswerIn(BaseModel):
    text: str = Field(min_length=10, max_length=3000)

    @field_validator("text")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 10:
            raise ValueError("Answer is too short")
        return v


class InterviewMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    seq: int
    role: InterviewRole
    kind: InterviewMessageKind
    question_index: int
    body: str
    created_at: datetime


class AnswerFeedback(BaseModel):
    index: int
    competency: str
    question: str
    score: int
    comment: str
    better: str


class Feedback(BaseModel):
    summary: str
    strengths: list[str]
    improvements: list[str]
    answers: list[AnswerFeedback]


class InterviewCard(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vacancy_id: uuid.UUID | None
    position: str
    company_name: str
    sector: Sector
    status: InterviewStatus
    score: float | None
    created_at: datetime
    finished_at: datetime | None


class InterviewDetail(InterviewCard):
    lang: str
    focus: list[str]
    requirements: dict[str, int]
    total_questions: int
    current: int
    messages: list[InterviewMessageOut]
    competency_scores: dict[str, float] | None
    feedback: Feedback | None


# ── Yordamchilar ──────────────────────────────────────────────────────


def _http(exc: flow.InterviewError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail)


async def _detail(db: AsyncSession, interview: Interview) -> InterviewDetail:
    completed = interview.status == InterviewStatus.COMPLETED
    feedback = None
    if completed and interview.feedback:
        raw = interview.feedback
        feedback = Feedback(
            summary=raw["summary"], strengths=raw["strengths"], improvements=raw["improvements"],
            answers=[
                AnswerFeedback(**a, question=interview.plan[a["index"]]["text"]) for a in raw["answers"]
            ],
        )
    return InterviewDetail(
        **InterviewCard.model_validate(interview).model_dump(),
        lang=interview.lang,
        focus=interview.focus,
        requirements=interview.requirements,
        total_questions=len(interview.plan),
        current=interview.current,
        messages=[InterviewMessageOut.model_validate(m) for m in await flow.messages(db, interview.id)],
        competency_scores=interview.competency_scores if completed else None,
        feedback=feedback,
    )


async def _reload(db: AsyncSession, user: User, interview_id: uuid.UUID) -> InterviewDetail:
    return await _detail(db, await flow.owned(db, user, interview_id))


# ── Endpointlar ───────────────────────────────────────────────────────


@router.post("", response_model=InterviewDetail, status_code=status.HTTP_201_CREATED)
async def start_interview(
    body: InterviewStart,
    user: Student,
    db: AsyncSession = Depends(get_db),
    now: datetime = Depends(get_now),
):
    try:
        interview = await flow.start(db, user, body.vacancy_id, body.lang, now)
    except flow.InterviewError as exc:
        await db.rollback()
        raise _http(exc)
    return await _reload(db, user, interview.id)


@router.get("", response_model=list[InterviewCard])
async def list_interviews(user: Student, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Interview).where(Interview.user_id == user.id)
        .order_by(Interview.created_at.desc()).limit(LIST_LIMIT)
    )).scalars()
    return [InterviewCard.model_validate(i) for i in rows]


@router.get("/{interview_id}", response_model=InterviewDetail)
async def get_interview(interview_id: uuid.UUID, user: Student, db: AsyncSession = Depends(get_db)):
    try:
        return await _detail(db, await flow.owned(db, user, interview_id))
    except flow.InterviewError as exc:
        raise _http(exc)


@router.post("/{interview_id}/answer", response_model=InterviewDetail)
async def answer_interview(
    interview_id: uuid.UUID,
    body: AnswerIn,
    user: Student,
    _: User = Depends(rate_limit("interview_answer", max_requests=10, window_seconds=60)),
    db: AsyncSession = Depends(get_db),
    now: datetime = Depends(get_now),
    queue=Depends(get_report_queue),
):
    try:
        finished = await flow.answer(db, user, interview_id, body.text, now)
    except flow.InterviewError as exc:
        await db.rollback()
        raise _http(exc)
    if finished:
        await enqueue_report(queue, interview_id)
    return await _reload(db, user, interview_id)


@router.post("/{interview_id}/abandon", response_model=InterviewDetail)
async def abandon_interview(
    interview_id: uuid.UUID, user: Student, db: AsyncSession = Depends(get_db), now: datetime = Depends(get_now),
):
    try:
        await flow.abandon(db, user, interview_id, now)
    except flow.InterviewError as exc:
        await db.rollback()
        raise _http(exc)
    return await _reload(db, user, interview_id)


@router.post("/{interview_id}/retry", response_model=InterviewDetail)
async def retry_interview(
    interview_id: uuid.UUID, user: Student, db: AsyncSession = Depends(get_db), queue=Depends(get_report_queue),
):
    try:
        await flow.retry(db, user, interview_id)
    except flow.InterviewError as exc:
        await db.rollback()
        raise _http(exc)
    await enqueue_report(queue, interview_id)
    return await _reload(db, user, interview_id)
