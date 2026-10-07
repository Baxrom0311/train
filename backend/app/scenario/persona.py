"""
Run ichidagi personaj chati (CONTRACT.md §9.4, §9.5).

Ikki bosqich, chunki LLM chaqiruvi bir necha soniya davom etadi va shu
vaqtda Run qatori qulflanib turmasligi kerak:

1. `accept_student_message` — qulflangan Run'da: tekshiruv, talaba xabarini
   yozish, limitlar va LLM uchun kontekst (`ReplyPlan`). Commit chaqiruvchida.
2. `produce_reply` — qulfsiz: RAG + LLM + anti-spoiler, keyin personaj
   javobini yozish va token hisobini oshirish.

AI chat Run holatini (hodisalar, ballar) o'zgartirmaydi.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, time, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.guardrail import validate_submission_content
from app.ai.persona_chat import ChatTurn, PersonaContext, persona_reply
from app.ai.spoiler import is_spoiler
from app.models.enums import ChatContentType, ChatSender, NodeType, RunEventStatus, RunStatus
from app.models.scenario import ChatMessage, Run, RunEvent, Scenario, ScenarioVersion, UploadedFile
from app.models.simulation import Submission
from app.scenario.engine import Conflict, Invalid, NotFound, definition_for
from app.scenario.holidays import load_calendar
from app.scenario.limits import DAILY_AI_MESSAGES, RUN_AI_TOKEN_BUDGET
from app.scenario.mentor import profile, student_work_lines
from app.scenario.rag import search
from app.scenario.schema import Persona, PersonaKind, ScenarioDefinition

HISTORY_LIMIT = 20

WEEKDAYS = ("dushanba", "seshanba", "chorshanba", "payshanba", "juma", "shanba", "yakshanba")


@dataclass(frozen=True)
class StudentMessage:
    text: str | None = None
    file_id: uuid.UUID | None = None
    link_url: str | None = None


@dataclass
class ReplyPlan:
    """`None` bo'lmagan `fallback` — LLM chaqirilmaydi, shu matn yuboriladi."""
    run_id: uuid.UUID
    version: ScenarioVersion
    persona: Persona
    context: PersonaContext | None
    history: list[ChatTurn]
    prompt: str
    references: list[str]
    fallback: str | None = None


def find_persona(defn: ScenarioDefinition, persona_key: str) -> Persona:
    persona = next((p for p in defn.personas if p.key == persona_key), None)
    if persona is None:
        raise NotFound("Personaj topilmadi")
    return persona


def _clock(now: datetime, tz) -> str:
    local = now.astimezone(tz)
    return f"{WEEKDAYS[local.weekday()]} {local:%H:%M}"


async def _run_state(db: AsyncSession, run: Run, defn: ScenarioDefinition, tz) -> tuple[list[str], list[str]]:
    """(Run holati qatorlari, mentor uchun ochiq task brief'lari)."""
    events = (await db.execute(
        select(RunEvent)
        .where(RunEvent.run_id == run.id, RunEvent.status.in_(
            (RunEventStatus.DELIVERED, RunEventStatus.SUBMITTED, RunEventStatus.MISSED)
        ))
        .order_by(RunEvent.delivered_at)
    )).scalars().all()
    lines, open_tasks = [], []
    for e in events:
        node = defn.node(e.node_id)
        if node.type == NodeType.MESSAGE:
            continue
        title = (node.brief or "Kun yakuni hisoboti").split("\n")[0][:100]
        due = f", dedlayn {e.due_at.astimezone(tz):%H:%M}" if e.due_at else ""
        lines.append(f"{title} — {e.status.value}{due}")
        if e.status != RunEventStatus.SUBMITTED and node.type in (NodeType.TASK, NodeType.INCIDENT):
            open_tasks.append(title)
    return lines, open_tasks


async def _student_work(db: AsyncSession, run: Run, defn: ScenarioDefinition) -> list[str]:
    """Mentor uchun: talabaning topshirgan ishlari va baholari (§9.13)."""
    events = (await db.execute(
        select(RunEvent).where(RunEvent.run_id == run.id, RunEvent.delivered_at.is_not(None))
        .order_by(RunEvent.delivered_at)
    )).scalars().all()
    subs = (await db.execute(
        select(Submission).where(Submission.run_id == run.id, Submission.run_event_id.is_not(None))
    )).scalars().all()
    return student_work_lines(defn, events, subs)


async def _ai_messages_today(db: AsyncSession, run_id: uuid.UUID, now: datetime, tz) -> int:
    day_start = datetime.combine(now.astimezone(tz).date(), time.min, tz)
    return await db.scalar(
        select(func.count(ChatMessage.id)).where(
            ChatMessage.run_id == run_id,
            ChatMessage.generated.is_(True),
            ChatMessage.created_at >= day_start,
        )
    ) or 0


async def history(db: AsyncSession, run_id: uuid.UUID, persona_key: str, limit: int | None = None) -> list[ChatMessage]:
    q = (
        select(ChatMessage)
        .where(ChatMessage.run_id == run_id, ChatMessage.persona_key == persona_key)
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id)
    )
    if limit:
        q = q.limit(limit)
    return list(reversed((await db.execute(q)).scalars().all()))


def _as_turn(m: ChatMessage, file_names: dict[uuid.UUID, str]) -> ChatTurn:
    body = m.body
    if m.file_id:
        body += f"\n[fayl: {file_names.get(m.file_id, 'fayl')}]"
    if m.link_url:
        body += f"\n[havola: {m.link_url}]"
    return ChatTurn("student" if m.sender == ChatSender.STUDENT else "persona", body.strip())


async def accept_student_message(
    db: AsyncSession, run: Run, persona_key: str, msg: StudentMessage, now: datetime
) -> tuple[ChatMessage, ReplyPlan]:
    """Run qulflangan va `advance_run` qilingan bo'lishi kerak."""
    if run.status != RunStatus.ACTIVE:
        raise Conflict("Run faol emas")
    version = await db.get(ScenarioVersion, run.scenario_version_id)
    defn = definition_for(version)
    persona = find_persona(defn, persona_key)

    text = (msg.text or "").strip()
    if not (text or msg.file_id or msg.link_url):
        raise Invalid("Xabar bo'sh")
    if msg.link_url:
        if not msg.link_url.startswith(("https://", "http://")):
            raise Invalid("Havola http(s):// bilan boshlansin")
        if not text:
            raise Invalid("Havola bilan qisqa izoh yozing")     # §9.5
    if text and not await validate_submission_content(text):
        raise Invalid("Xabar qabul qilinmadi")
    file_name = None
    if msg.file_id is not None:
        f = await db.get(UploadedFile, msg.file_id)
        if f is None or f.owner_user_id != run.user_id or f.run_id not in (None, run.id):
            raise Invalid("Fayl topilmadi")
        file_name = f.original_name

    previous = await history(db, run.id, persona_key, HISTORY_LIMIT)
    student = ChatMessage(
        run_id=run.id,
        persona_key=persona_key,
        sender=ChatSender.STUDENT,
        content_type=(
            ChatContentType.FILE if msg.file_id else ChatContentType.LINK if msg.link_url else ChatContentType.TEXT
        ),
        body=text,
        file_id=msg.file_id,
        link_url=msg.link_url,
        created_at=now,
    )
    db.add(student)
    await db.flush()

    plan = ReplyPlan(
        run_id=run.id, version=version, persona=persona, context=None,
        history=[], prompt="", references=[],
    )
    cal = await load_calendar(db)
    if (
        run.ai_tokens_used >= RUN_AI_TOKEN_BUDGET
        or await _ai_messages_today(db, run.id, now, cal.tz) >= DAILY_AI_MESSAGES
    ):
        plan.fallback = persona.busy_reply
        return student, plan

    file_names = {msg.file_id: file_name} if msg.file_id else {}
    file_ids = [m.file_id for m in previous if m.file_id]
    if file_ids:
        rows = (await db.execute(
            select(UploadedFile.id, UploadedFile.original_name).where(UploadedFile.id.in_(file_ids))
        )).all()
        file_names.update(dict(rows))

    scenario = await db.get(Scenario, version.scenario_id)
    state_lines, open_tasks = await _run_state(db, run, defn, cal.tz)
    is_mentor = persona.kind == PersonaKind.MENTOR
    plan.context = PersonaContext(
        persona=profile(persona),
        company_name=scenario.company_name,
        scenario_title=scenario.title,
        local_time=_clock(now, cal.tz),
        run_state=tuple(state_lines),
        open_tasks=tuple(open_tasks) if is_mentor else (),
        student_work=tuple(await _student_work(db, run, defn)) if is_mentor else (),
    )
    plan.history = [_as_turn(m, file_names) for m in previous]
    plan.prompt = _as_turn(student, file_names).body
    plan.references = [n.reference_answer for n in defn.nodes if n.reference_answer]
    return student, plan


async def produce_reply(
    db: AsyncSession,
    plan: ReplyPlan,
    now: datetime,
    *,
    reply_fn=None,
    spoiler_fn=None,
    search_fn=None,
) -> ChatMessage:
    """Qulfsiz. Personaj javobini yozadi va commit qiladi."""
    reply_fn = reply_fn or persona_reply
    spoiler_fn = spoiler_fn or is_spoiler
    search_fn = search_fn or search
    body, generated, tokens = plan.fallback, False, 0
    if body is None:
        passages = await search_fn(db, plan.version, plan.persona.key, plan.prompt)
        ctx = PersonaContext(**{**plan.context.__dict__, "passages": tuple(passages)})
        result = await reply_fn(ctx, plan.history, plan.prompt)
        if result is None:
            body = plan.persona.busy_reply
        else:
            tokens = result.tokens
            if await spoiler_fn(result.text, plan.references):
                body = plan.persona.deflect_reply
            else:
                body, generated = result.text.strip(), True

    reply = ChatMessage(
        run_id=plan.run_id,
        persona_key=plan.persona.key,
        sender=ChatSender.PERSONA,
        body=body,
        generated=generated,
        # talaba xabari bilan bir xil `now` — tartib aniq bo'lsin
        created_at=now + timedelta(microseconds=1),
    )
    db.add(reply)
    if tokens:
        await db.execute(
            update(Run).where(Run.id == plan.run_id).values(ai_tokens_used=Run.ai_tokens_used + tokens)
        )
    await db.commit()
    return reply
