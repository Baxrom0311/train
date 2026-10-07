"""
Run API (CONTRACT.md §9.9, Modul 9). Barcha `runs/*` — faqat Run egasi,
boshqa foydalanuvchiga 404.

Har so'rov Run'ni qulflab `advance_run` qiladi (cron kechiksa ham talaba
to'g'ri holatni ko'radi), keyin `last_activity_at` yangilanadi. Talabaga
faqat yetkazilgan hodisalar ko'rinadi; rubrika, hint, namunaviy javob va
qaror variantlarining bahosi hech qachon chiqmaydi.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.scenarios import PersonaPublic, published_version
from app.core.deps import get_current_active_user
from app.core.redis_client import get_arq_pool
from app.database import get_db
from app.models.enums import AIEvalStatus, NodeType, RunEventStatus, RunStatus, Sector
from app.models.scenario import Run, RunEvent, ScenarioVersion
from app.models.simulation import Submission
from app.models.user import User
from app.scenario import notify
from app.scenario.engine import (
    OPEN_STATUSES,
    Answer,
    EngineError,
    Note,
    abandon,
    advance_run,
    create_run,
    decide,
    definition_for,
    lock_run,
    submit_answer,
)
from app.scenario.holidays import load_calendar
from app.scenario.jobs import enqueue_evaluation

router = APIRouter(tags=["runs"])

VISIBLE_STATUSES = (RunEventStatus.DELIVERED, RunEventStatus.SUBMITTED, RunEventStatus.MISSED)


def get_now() -> datetime:
    """Testlarda `dependency_overrides` bilan aniq vaqt beriladi."""
    return datetime.now(timezone.utc)


async def get_eval_queue():
    return await get_arq_pool()


# ── Sxemalar ──────────────────────────────────────────────────────────


class RunCreate(BaseModel):
    scenario_id: uuid.UUID
    start_at: datetime | None = None


class OptionOut(BaseModel):
    key: str
    label: str


class EventOut(BaseModel):
    node_id: str
    type: NodeType
    from_persona: str | None
    brief: str
    attachments: list[str]
    answer_types: list[str]
    options: list[OptionOut]
    status: RunEventStatus
    delivered_at: datetime | None
    due_at: datetime | None
    choice: str | None
    attempts_used: int
    max_attempts: int
    last_score: float | None
    last_feedback: str | None
    last_eval_status: AIEvalStatus | None


class ScenarioBrief(BaseModel):
    id: uuid.UUID
    slug: str
    title: str
    sector: Sector
    company_name: str
    duration_days: int


class RunOut(BaseModel):
    id: uuid.UUID
    status: RunStatus
    start_at: datetime
    ends_at: datetime
    scenario: ScenarioBrief


class RunDetailOut(RunOut):
    now: datetime
    local_time: str
    is_work_time: bool
    personas: list[PersonaPublic]
    events: list[EventOut]


class RunCreatedOut(BaseModel):
    run: RunDetailOut
    warning: str | None
    day1_ends_at: datetime


class SubmitIn(BaseModel):
    text: str | None = Field(default=None, max_length=10_000)
    code: str | None = Field(default=None, max_length=10_000)
    file_id: uuid.UUID | None = None
    link_url: str | None = Field(default=None, max_length=2048)


class DecideIn(BaseModel):
    option: str = Field(min_length=1, max_length=64)


class SubmissionResult(BaseModel):
    submission_id: uuid.UUID
    attempt: int
    late: bool
    ai_eval_status: AIEvalStatus
    score: float | None
    run: RunDetailOut


# ── Yordamchilar ──────────────────────────────────────────────────────


def _engine_error(exc: EngineError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail)


def _scenario_brief(run: Run) -> ScenarioBrief:
    s = run.scenario_version.scenario
    return ScenarioBrief(
        id=s.id, slug=s.slug, title=s.title, sector=s.sector,
        company_name=s.company_name, duration_days=s.duration_days,
    )


async def _locked(db: AsyncSession, run_id: uuid.UUID, user: User, now: datetime) -> tuple[Run, list[Note]]:
    try:
        run = await lock_run(db, run_id, user.id)
    except EngineError as exc:
        raise _engine_error(exc)
    notes = await advance_run(db, run, now)
    # §9.2: avval advance (7 kunlik yonish tekshiruvi), keyin faollik
    if run.status in OPEN_STATUSES:
        run.last_activity_at = now
    return run, notes


async def _detail(db: AsyncSession, run: Run, now: datetime) -> RunDetailOut:
    run = (await db.execute(
        select(Run).where(Run.id == run.id).options(
            selectinload(Run.scenario_version).selectinload(ScenarioVersion.scenario)
        )
    )).scalars().one()
    defn = definition_for(run.scenario_version)
    cal = await load_calendar(db)
    events = (await db.execute(
        select(RunEvent)
        .where(RunEvent.run_id == run.id, RunEvent.status.in_(VISIBLE_STATUSES))
        .order_by(RunEvent.delivered_at, RunEvent.node_id)
    )).scalars().all()
    subs = (await db.execute(
        select(Submission).where(Submission.run_id == run.id).order_by(Submission.attempt)
    )).scalars().all()
    by_event: dict[uuid.UUID, list[Submission]] = {}
    for s in subs:
        by_event.setdefault(s.run_event_id, []).append(s)

    out = []
    for e in events:
        node = defn.node(e.node_id)
        attempts = by_event.get(e.id, [])
        last = attempts[-1] if attempts else None
        out.append(EventOut(
            node_id=node.id,
            type=node.type,
            from_persona=node.from_,
            brief=node.brief,
            attachments=node.attachments,
            answer_types=[t.value for t in node.answer_types],
            options=[OptionOut(key=o.key, label=o.label) for o in node.options],
            status=e.status,
            delivered_at=e.delivered_at,
            due_at=e.due_at,
            choice=e.choice,
            attempts_used=len(attempts),
            max_attempts=1 if node.type == NodeType.DECISION else node.max_attempts,
            last_score=last.ai_score if last else None,
            last_feedback=last.ai_feedback if last else None,
            last_eval_status=last.ai_eval_status if last else None,
        ))
    local = now.astimezone(cal.tz)
    return RunDetailOut(
        id=run.id,
        status=run.status,
        start_at=run.start_at,
        ends_at=run.ends_at,
        scenario=_scenario_brief(run),
        now=now,
        local_time=local.isoformat(),
        is_work_time=cal.is_workday(local.date()) and cal.is_work_time(local.time()),
        personas=[
            PersonaPublic(key=p.key, name=p.name, role=p.role, kind=p.kind.value) for p in defn.personas
        ],
        events=out,
    )


# ── Endpointlar ───────────────────────────────────────────────────────


@router.post("/runs", response_model=RunCreatedOut, status_code=status.HTTP_201_CREATED)
async def start_run(
    body: RunCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
    now: datetime = Depends(get_now),
):
    _, version = await published_version(db, body.scenario_id)
    try:
        run, info = await create_run(db, user.id, version, now, body.start_at)
        notes = await advance_run(db, run, now)
        await db.commit()
    except EngineError as exc:
        await db.rollback()
        raise _engine_error(exc)
    except IntegrityError:
        # parallel so'rov: qisman UNIQUE (bitta ochiq Run) ushladi
        await db.rollback()
        raise HTTPException(status_code=409, detail="Bu ssenariyda tugallanmagan Run bor")
    await notify.publish(notes)
    return RunCreatedOut(run=await _detail(db, run, now), warning=info.warning, day1_ends_at=info.day1_ends_at)


@router.get("/runs/my", response_model=list[RunOut])
async def my_runs(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    runs = (await db.execute(
        select(Run)
        .where(Run.user_id == user.id)
        .options(selectinload(Run.scenario_version).selectinload(ScenarioVersion.scenario))
        .order_by(Run.created_at.desc())
    )).scalars().all()
    return [
        RunOut(id=r.id, status=r.status, start_at=r.start_at, ends_at=r.ends_at, scenario=_scenario_brief(r))
        for r in runs
    ]


@router.get("/runs/{run_id}", response_model=RunDetailOut)
async def get_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
    now: datetime = Depends(get_now),
):
    run, notes = await _locked(db, run_id, user, now)
    await db.commit()
    await notify.publish(notes)
    return await _detail(db, run, now)


@router.post("/runs/{run_id}/events/{node_id}/submit", response_model=SubmissionResult)
async def submit(
    run_id: uuid.UUID,
    node_id: str,
    body: SubmitIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
    now: datetime = Depends(get_now),
    queue=Depends(get_eval_queue),
):
    run, notes = await _locked(db, run_id, user, now)
    try:
        sub, more = await submit_answer(db, run, node_id, Answer(**body.model_dump()), now)
    except EngineError as exc:
        await db.commit()  # advance natijasi saqlansin
        await notify.publish(notes)
        raise _engine_error(exc)
    await db.commit()
    await notify.publish(notes + more)
    await enqueue_evaluation(queue, sub.id)
    return SubmissionResult(
        submission_id=sub.id, attempt=sub.attempt, late=sub.late,
        ai_eval_status=sub.ai_eval_status, score=sub.ai_score, run=await _detail(db, run, now),
    )


@router.post("/runs/{run_id}/events/{node_id}/decide", response_model=SubmissionResult)
async def decide_event(
    run_id: uuid.UUID,
    node_id: str,
    body: DecideIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
    now: datetime = Depends(get_now),
):
    run, notes = await _locked(db, run_id, user, now)
    try:
        sub, more = await decide(db, run, node_id, body.option, now)
    except EngineError as exc:
        await db.commit()
        await notify.publish(notes)
        raise _engine_error(exc)
    await db.commit()
    await notify.publish(notes + more)
    return SubmissionResult(
        submission_id=sub.id, attempt=sub.attempt, late=sub.late,
        ai_eval_status=sub.ai_eval_status, score=sub.ai_score, run=await _detail(db, run, now),
    )


@router.post("/runs/{run_id}/abandon", response_model=RunDetailOut)
async def abandon_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
    now: datetime = Depends(get_now),
):
    run, notes = await _locked(db, run_id, user, now)
    try:
        notes += await abandon(db, run, now)
    except EngineError as exc:
        await db.commit()
        await notify.publish(notes)
        raise _engine_error(exc)
    await db.commit()
    await notify.publish(notes)
    return await _detail(db, run, now)
