"""
Run API (CONTRACT.md §9.9, Modul 9). Barcha `runs/*` — faqat Run egasi
yoki jamoaviy Run'ning faol a'zosi (§29.3), boshqa foydalanuvchiga 404.

Har so'rov Run'ni qulflab `advance_run` qiladi (cron kechiksa ham talaba
to'g'ri holatni ko'radi), keyin `last_activity_at` yangilanadi. Talabaga
faqat yetkazilgan hodisalar ko'rinadi; rubrika, hint, namunaviy javob va
qaror variantlarining bahosi hech qachon chiqmaydi.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import exists, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.scenarios import PersonaPublic, published_version
from app.core.deps import get_current_active_user, rate_limit
from app.core.redis_client import get_arq_pool, redis_client
from app.database import get_db
from app.models.enums import AIEvalStatus, ChatContentType, ChatSender, NodeType, RunEventStatus, RunStatus, Sector
from app.models.scenario import ChatMessage, Run, RunEvent, RunTeamMember, ScenarioVersion
from app.models.simulation import Submission
from app.models.user import User
from app.scenario import notify
from app.ai.guardrail import validate_submission_content
from app.scenario.engine import (
    OPEN_STATUSES,
    TEAM_CHANNEL,
    Answer,
    EngineError,
    Note,
    abandon,
    advance_run,
    create_run,
    decide,
    definition_for,
    lock_run,
    participant_of,
    submit_answer,
    take_hint,
)
from app.scenario.holidays import load_calendar
from app.scenario.evaluation import public_checks
from app.scenario.jobs import enqueue_evaluation
from app.scenario.persona import (
    StudentMessage,
    accept_student_message,
    find_persona,
    history,
    produce_reply,
)
from app.scenario.team import TeamView, leave_run, team_view

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


class AttachmentOut(BaseModel):
    key: str
    title: str


class ChecksOut(BaseModel):
    """Yashirin testlar natijasi (§19.4) — faqat sonlar va yiqilgan test nomlari."""
    status: str
    passed: int
    total: int
    failed: list[str]


class SubmittedBy(BaseModel):
    user_id: uuid.UUID
    name: str


class EventOut(BaseModel):
    node_id: str
    type: NodeType
    from_persona: str | None
    brief: str
    attachments: list[AttachmentOut]
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
    last_checks: ChecksOut | None = None
    # §29.3: jamoaviy Run'da — node roli va oxirgi urinish muallifi
    role: str | None = None
    submitted_by: SubmittedBy | None = None


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
    # §29: jamoaviy Run — a'zolar soni (yakka Run'da null), kapitanmi, jamoadan chiqqanmi
    team_size: int | None = None
    is_captain: bool = True
    left: bool = False


class TeamRoleOut(BaseModel):
    key: str
    title: str
    summary: str
    holder_id: uuid.UUID | None


class TeamMemberOut(BaseModel):
    user_id: uuid.UUID
    name: str
    roles: list[str]
    is_captain: bool


class RunTeamOut(BaseModel):
    id: uuid.UUID
    captain_id: uuid.UUID
    me: uuid.UUID
    my_roles: list[str]
    roles: list[TeamRoleOut]
    members: list[TeamMemberOut]      # faol a'zolar, qo'shilish tartibida


class RunDetailOut(RunOut):
    now: datetime
    local_time: str
    is_work_time: bool
    personas: list[PersonaPublic]
    events: list[EventOut]
    team: RunTeamOut | None = None


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


def _member_or_owner(user_id: uuid.UUID):
    """Hisobot va ro'yxat uchun: chiqib ketgan a'zo ham (§29.3)."""
    return or_(
        Run.user_id == user_id,
        exists().where(RunTeamMember.team_id == Run.team_id, RunTeamMember.user_id == user_id),
    )


def _run_team(team: TeamView, me: uuid.UUID) -> RunTeamOut:
    return RunTeamOut(
        id=team.team_id,
        captain_id=team.captain_id,
        me=me,
        my_roles=list(team.member(me).roles) if team.member(me) else [],
        roles=[
            TeamRoleOut(key=r.key, title=r.title, summary=r.summary, holder_id=team.holder(r.key))
            for r in team.spec.roles
        ],
        members=[
            TeamMemberOut(user_id=m.user_id, name=m.name, roles=list(m.roles), is_captain=m.user_id == team.captain_id)
            for m in team.active
        ],
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


async def _detail(db: AsyncSession, run: Run, now: datetime, me: uuid.UUID) -> RunDetailOut:
    run = (await db.execute(
        select(Run).where(Run.id == run.id).options(
            selectinload(Run.scenario_version).selectinload(ScenarioVersion.scenario)
        )
    )).scalars().one()
    defn = definition_for(run.scenario_version)
    team = await team_view(db, run, defn)
    cal = await load_calendar(db)
    events = (await db.execute(
        select(RunEvent)
        .where(RunEvent.run_id == run.id, RunEvent.status.in_(VISIBLE_STATUSES))
    )).scalars().all()
    order = {n.id: i for i, n in enumerate(defn.nodes)}
    events = sorted(events, key=lambda e: (e.delivered_at, order[e.node_id]))
    subs = (await db.execute(
        select(Submission).where(Submission.run_id == run.id).order_by(Submission.attempt)
    )).scalars().all()
    by_event: dict[uuid.UUID, list[Submission]] = {}
    for s in subs:
        by_event.setdefault(s.run_event_id, []).append(s)

    docs = {d.key: d.title for d in defn.documents}
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
            attachments=[AttachmentOut(key=k, title=docs[k]) for k in node.attachments],
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
            last_checks=public_checks(last.check_results) if last else None,
            role=node.role if team else None,
            submitted_by=(
                SubmittedBy(user_id=last.user_id, name=team.name(last.user_id) or "")
                if team and last else None
            ),
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
        team_size=len(team.active) if team else None,
        is_captain=run.user_id == me,
        team=_run_team(team, me) if team else None,
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
    return RunCreatedOut(run=await _detail(db, run, now, user.id), warning=info.warning, day1_ends_at=info.day1_ends_at)


@router.get("/runs/my", response_model=list[RunOut])
async def my_runs(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    runs = (await db.execute(
        select(Run)
        .where(_member_or_owner(user.id))
        .options(selectinload(Run.scenario_version).selectinload(ScenarioVersion.scenario))
        .order_by(Run.created_at.desc())
    )).scalars().all()
    team_ids = [r.team_id for r in runs if r.team_id]
    seats: dict[uuid.UUID, list[RunTeamMember]] = {}
    if team_ids:
        for m in (await db.execute(select(RunTeamMember).where(RunTeamMember.team_id.in_(team_ids)))).scalars():
            seats.setdefault(m.team_id, []).append(m)
    out = []
    for r in runs:
        members = seats.get(r.team_id, [])
        me = next((m for m in members if m.user_id == user.id), None)
        out.append(RunOut(
            id=r.id, status=r.status, start_at=r.start_at, ends_at=r.ends_at, scenario=_scenario_brief(r),
            team_size=sum(m.left_at is None for m in members) if r.team_id else None,
            is_captain=r.user_id == user.id,
            left=me is not None and me.left_at is not None,
        ))
    return out


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
    return await _detail(db, run, now, user.id)


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
        sub, more = await submit_answer(db, run, node_id, Answer(**body.model_dump()), now, actor_id=user.id)
    except EngineError as exc:
        await db.commit()  # advance natijasi saqlansin
        await notify.publish(notes)
        raise _engine_error(exc)
    await db.commit()
    await notify.publish(notes + more)
    await enqueue_evaluation(queue, sub.id)
    return SubmissionResult(
        submission_id=sub.id, attempt=sub.attempt, late=sub.late,
        ai_eval_status=sub.ai_eval_status, score=sub.ai_score, run=await _detail(db, run, now, user.id),
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
        sub, more = await decide(db, run, node_id, body.option, now, actor_id=user.id)
    except EngineError as exc:
        await db.commit()
        await notify.publish(notes)
        raise _engine_error(exc)
    await db.commit()
    await notify.publish(notes + more)
    return SubmissionResult(
        submission_id=sub.id, attempt=sub.attempt, late=sub.late,
        ai_eval_status=sub.ai_eval_status, score=sub.ai_score, run=await _detail(db, run, now, user.id),
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
        notes += await abandon(db, run, now, actor_id=user.id if run.team_id else None)
    except EngineError as exc:
        await db.commit()
        await notify.publish(notes)
        raise _engine_error(exc)
    await db.commit()
    await notify.publish(notes)
    return await _detail(db, run, now, user.id)


@router.post("/runs/{run_id}/leave", response_model=RunOut)
async def leave_team_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
    now: datetime = Depends(get_now),
):
    """§29.3: a'zo jamoadan chiqadi, rollari qolganlarga o'tadi. Shundan keyin faqat hisobot ochiq."""
    run, notes = await _locked(db, run_id, user, now)
    try:
        notes += await leave_run(db, run, user.id, now)
    except EngineError as exc:
        await db.commit()
        await notify.publish(notes)
        raise _engine_error(exc)
    await db.commit()
    await notify.publish(notes)
    run = (await db.execute(
        select(Run).where(Run.id == run.id)
        .options(selectinload(Run.scenario_version).selectinload(ScenarioVersion.scenario))
    )).scalars().one()
    return RunOut(
        id=run.id, status=run.status, start_at=run.start_at, ends_at=run.ends_at, scenario=_scenario_brief(run),
        is_captain=False, left=True,
    )


# ── Hint (§9.4) ───────────────────────────────────────────────────────


class HintOut(BaseModel):
    hint: str
    hints_used: int
    hints_left: int
    penalty: float


@router.post("/runs/{run_id}/events/{node_id}/hint", response_model=HintOut)
async def hint(
    run_id: uuid.UUID,
    node_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
    now: datetime = Depends(get_now),
):
    run, notes = await _locked(db, run_id, user, now)
    try:
        info, more = await take_hint(db, run, node_id, now, actor_id=user.id)
    except EngineError as exc:
        await db.commit()
        await notify.publish(notes)
        raise _engine_error(exc)
    await db.commit()
    await notify.publish(notes + more)
    return HintOut(**info.__dict__)


# ── Personaj chati (§9.4, §9.5) ───────────────────────────────────────


class ChatIn(BaseModel):
    text: str | None = Field(default=None, max_length=4000)
    file_id: uuid.UUID | None = None
    link_url: str | None = Field(default=None, max_length=2048)


class ChatMessageOut(BaseModel):
    id: uuid.UUID
    persona_key: str
    sender: ChatSender
    content_type: ChatContentType
    body: str
    file_id: uuid.UUID | None
    link_url: str | None
    generated: bool
    created_at: datetime
    # mentorning o'zi boshlagan xabari (§9.13): review | nudge
    purpose: str | None = None
    node_id: str | None = None
    # §29.3: talaba xabarining muallifi; ism faqat jamoaviy Run'da
    author_id: uuid.UUID | None = None
    author_name: str | None = None

    model_config = {"from_attributes": True}


def _chat_out(messages: list[ChatMessage], team: TeamView | None) -> list[ChatMessageOut]:
    out = []
    for m in messages:
        item = ChatMessageOut.model_validate(m)
        if team is not None and m.author_id is not None:
            item.author_name = team.name(m.author_id)
        out.append(item)
    return out


class ChatExchangeOut(BaseModel):
    message: ChatMessageOut
    reply: ChatMessageOut


@router.get("/runs/{run_id}/chat/{persona_key}", response_model=list[ChatMessageOut])
async def get_chat(
    run_id: uuid.UUID,
    persona_key: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
    now: datetime = Depends(get_now),
):
    run, notes = await _locked(db, run_id, user, now)
    defn = definition_for(run.scenario_version)
    try:
        find_persona(defn, persona_key)
    except EngineError as exc:
        raise _engine_error(exc)
    await db.commit()
    await notify.publish(notes)
    return _chat_out(await history(db, run.id, persona_key), await team_view(db, run, defn))


@router.post("/runs/{run_id}/chat/{persona_key}", response_model=ChatExchangeOut)
async def post_chat(
    run_id: uuid.UUID,
    persona_key: str,
    body: ChatIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(rate_limit("persona_chat", max_requests=10, window_seconds=60)),
    now: datetime = Depends(get_now),
):
    run, notes = await _locked(db, run_id, user, now)
    try:
        message, plan = await accept_student_message(
            db, run, persona_key, StudentMessage(**body.model_dump()), now, author_id=user.id,
        )
    except EngineError as exc:
        await db.commit()
        await notify.publish(notes)
        raise _engine_error(exc)
    await db.commit()          # qulf LLM chaqiruvidan oldin bo'shatiladi
    await notify.publish(notes)
    reply = await produce_reply(db, plan, now)
    await notify.publish([Note(run.id, "chat_message", {"persona_key": persona_key, "id": str(reply.id)})])
    message_out, reply_out = _chat_out([message, reply], await team_view(db, run))
    return ChatExchangeOut(message=message_out, reply=reply_out)


# ── Jamoa chati (§29.3) ───────────────────────────────────────────────

TEAM_CHAT_MAX = 2000


class TeamChatIn(BaseModel):
    text: str = Field(min_length=1, max_length=TEAM_CHAT_MAX)


async def _locked_team(db: AsyncSession, run_id: uuid.UUID, user: User, now: datetime) -> tuple[Run, list[Note]]:
    run, notes = await _locked(db, run_id, user, now)
    if run.team_id is None:
        await db.commit()
        await notify.publish(notes)
        raise HTTPException(status_code=404, detail="Bu Run jamoaviy emas")
    return run, notes


@router.get("/runs/{run_id}/team-chat", response_model=list[ChatMessageOut])
async def get_team_chat(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
    now: datetime = Depends(get_now),
):
    run, notes = await _locked_team(db, run_id, user, now)
    await db.commit()
    await notify.publish(notes)
    return _chat_out(await history(db, run.id, TEAM_CHANNEL), await team_view(db, run))


@router.post("/runs/{run_id}/team-chat", response_model=ChatMessageOut, status_code=status.HTTP_201_CREATED)
async def post_team_chat(
    run_id: uuid.UUID,
    body: TeamChatIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(rate_limit("team_chat", max_requests=20, window_seconds=60)),
    now: datetime = Depends(get_now),
):
    """A'zolar orasida; AI javob bermaydi. Matn kun/yakuniy hisobot AI'siga ham boradi — guardrail shart."""
    run, notes = await _locked_team(db, run_id, user, now)
    text = body.text.strip()
    error = None
    if run.status != RunStatus.ACTIVE:
        error = HTTPException(status_code=409, detail="Run faol emas")
    elif not text:
        error = HTTPException(status_code=422, detail="Xabar bo'sh")
    elif not await validate_submission_content(text):
        error = HTTPException(status_code=422, detail="Xabar qabul qilinmadi")
    if error is not None:
        await db.commit()
        await notify.publish(notes)
        raise error
    message = ChatMessage(
        run_id=run.id, persona_key=TEAM_CHANNEL, sender=ChatSender.STUDENT, body=text,
        created_at=now, author_id=user.id,
    )
    db.add(message)
    await db.commit()
    await notify.publish(notes + [Note(run.id, "chat_message", {"persona_key": TEAM_CHANNEL, "id": str(message.id)})])
    return _chat_out([message], await team_view(db, run))[0]


# ── SSE (§9.8) ────────────────────────────────────────────────────────


@router.get("/runs/{run_id}/stream")
async def stream(
    run_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """
    `text/event-stream`. Auth — `Authorization` header (brauzerda
    `fetch` asosidagi SSE mijozi bilan; `EventSource` header yubora olmaydi).
    """
    owned = await db.scalar(select(Run.id).where(Run.id == run_id, participant_of(user.id)))
    if owned is None:
        raise HTTPException(status_code=404, detail="Run topilmadi")
    await db.close()   # uzoq ulanish DB ulanishini ushlab turmasin
    return StreamingResponse(
        notify.sse_events(redis_client, run_id, is_disconnected=request.is_disconnected),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Hisobotlar (§9.6) ─────────────────────────────────────────────────


class ReportOut(BaseModel):
    run_id: uuid.UUID
    status: RunStatus
    days: list[dict]
    final: dict | None
    competency_scores: dict | None
    # Run yopilgan, lekin yakuniy hisobot hali yozilmoqda (baholash kutilmoqda)
    final_pending: bool


@router.get("/runs/{run_id}/report", response_model=ReportOut)
async def get_report(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    run = (await db.execute(select(Run).where(Run.id == run_id, _member_or_owner(user.id)))).scalars().first()
    if run is None:
        raise HTTPException(status_code=404, detail="Run topilmadi")
    results = (await db.execute(select(RunEvent.result).where(RunEvent.run_id == run.id))).scalars().all()
    days = sorted((r["report"] for r in results if r and r.get("report")), key=lambda d: d["day"])
    return ReportOut(
        run_id=run.id,
        status=run.status,
        days=days,
        final=run.final_report,
        competency_scores=run.competency_scores,
        final_pending=run.status in (RunStatus.COMPLETED, RunStatus.EXPIRED) and run.final_report is None,
    )


class DocumentOut(BaseModel):
    key: str
    title: str
    content: str


@router.get("/runs/{run_id}/documents/{key}", response_model=DocumentOut)
async def get_document(
    run_id: uuid.UUID,
    key: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
    now: datetime = Depends(get_now),
):
    """Faqat yetkazilgan hodisaga biriktirilgan hujjat; qolganlari — 404 (§9.3.2)."""
    run, notes = await _locked(db, run_id, user, now)
    defn = definition_for(await db.get(ScenarioVersion, run.scenario_version_id))
    visible = (await db.execute(
        select(RunEvent.node_id).where(RunEvent.run_id == run.id, RunEvent.status.in_(VISIBLE_STATUSES))
    )).scalars().all()
    await db.commit()
    await notify.publish(notes)
    if not any(key in defn.node(node_id).attachments for node_id in visible):
        raise HTTPException(status_code=404, detail="Hujjat topilmadi")
    doc = next(d for d in defn.documents if d.key == key)
    return DocumentOut(key=doc.key, title=doc.title, content=doc.content)
