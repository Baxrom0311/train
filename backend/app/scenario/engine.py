"""
Run dvigateli (CONTRACT.md §9.2, §9.8). Barcha holat o'tishlari shu yerda.

- `create_run` — Run va vaqti aniq (`day`+`at`) node'lar uchun `run_events`.
- `advance(db, now, run_id=None)` — vaqti kelgan hodisalarni yetkazadi
  (`when` tekshiruvi bilan), dedlayni o'tganlarni `missed` qiladi, Run'ni
  `active` / `completed` / `expired` holatiga o'tkazadi. Cron (hamma Run)
  va API (bitta Run) shu funksiyani chaqiradi.
- `submit_answer`, `decide`, `abandon` — talaba harakatlari.

`now` doim parametr. Run qatori `SELECT ... FOR UPDATE` bilan qulflanadi:
cron band Run'ni o'tkazib yuboradi (`SKIP LOCKED`), API kutadi. Holatlar
faqat oldinga o'tadi (`pending → delivered|skipped`, `delivered → missed|
submitted`, `missed → submitted`), shuning uchun qayta chaqiruv xavfsiz.
Commit chaqiruvchida; qaytgan `Note`lar commit'dan keyin `notify.publish`
orqali `run:{id}` kanaliga yuboriladi.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import DateTime, and_, exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.guardrail import MAX_CONTENT_LENGTH
from app.models.enums import AIEvalStatus, ChatSender, NodeType, RunEventStatus, RunStatus
from app.models.scenario import CHAT_PURPOSE_NUDGE, ChatMessage, Run, RunEvent, ScenarioVersion, UploadedFile
from app.models.simulation import Submission
from app.scenario.clock import WorkCalendar
from app.scenario.conditions import ConditionContext, evaluate, pending_scores
from app.scenario.holidays import load_calendar
from app.scenario.schema import ANSWER_TYPES, AnswerType, Node, ScenarioDefinition, short_title

# §9.3.3 — `score_*` sharti uchun baho kutish chegarasi
SCORE_WAIT = timedelta(minutes=15)
# §9.2 — shuncha vaqt faollik bo'lmasa Run yonadi
INACTIVITY_LIMIT = timedelta(days=7)
# `due_in_minutes` berilmagan baholanadigan node'lar uchun (ish daqiqasi)
DEFAULT_DUE_MINUTES = {NodeType.DECISION: 60, NodeType.DAY_END: 30}
# §9.3.2 — qaror varianti bahosi
DECISION_SCORES = {"correct": 100.0, "acceptable": 60.0, "wrong": 0.0}

OPEN_STATUSES = (RunStatus.SCHEDULED, RunStatus.ACTIVE)
# `day_end` yopilganda `run_events.result`ga — kunlik hisobot yozilishi kerak (§9.6)
REPORT_DUE = "report_due"
AWAITING_EVAL = (AIEvalStatus.PENDING, AIEvalStatus.QUEUED_RETRY)
# §9.13 — mentor eslatmasi: `run_events.result` kalitlari va oyna (ish daqiqasi)
NUDGE_AT = "nudge_at"
NUDGE_MIN_WINDOW = 45
NUDGE_MAX_LEAD = 30


# ── Xatolar (API HTTP kodiga aylantiradi) ──────────────────────────────


class EngineError(Exception):
    status_code = 400

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class NotFound(EngineError):
    status_code = 404


class Conflict(EngineError):
    status_code = 409


class Invalid(EngineError):
    status_code = 422


@dataclass(frozen=True)
class Note:
    """SSE uchun bildirishnoma (§9.8): `type` — run_status, event_delivered, ..."""
    run_id: uuid.UUID
    type: str
    data: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Answer:
    text: str | None = None
    code: str | None = None
    file_id: uuid.UUID | None = None
    link_url: str | None = None

    def kinds(self) -> set[AnswerType]:
        given = {
            AnswerType.TEXT: self.text,
            AnswerType.CODE: self.code,
            AnswerType.FILE: self.file_id,
            AnswerType.LINK: self.link_url,
        }
        return {kind for kind, value in given.items() if value}

    def content(self) -> str:
        parts = []
        if self.text:
            parts.append(self.text.strip())
        if self.code:
            parts.append(f"```\n{self.code.rstrip()}\n```")
        return "\n\n".join(parts)


@dataclass(frozen=True)
class StartInfo:
    warning: str | None
    day1_ends_at: datetime


# ── Ssenariy ta'rifi ──────────────────────────────────────────────────

# Versiya ta'rifi yaratilgandan keyin o'zgarmaydi (tahrir = yangi versiya).
# Kalit — (versiya, oxirgi yozilgan vaqt): qoralama joyida yangilansa (§16.1)
# `created_at` o'zgaradi, shuning uchun boshqa jarayonlar (API worker'lari,
# arq) ham eski ta'rifni ishlatmaydi — keshni tozalash xabari kerak emas.
_DEFINITIONS: dict[tuple[uuid.UUID, datetime], ScenarioDefinition] = {}


def definition_for(version: ScenarioVersion) -> ScenarioDefinition:
    key = (version.id, version.created_at)
    defn = _DEFINITIONS.get(key)
    if defn is None:
        defn = ScenarioDefinition.model_validate(version.definition)
        _DEFINITIONS[key] = defn
    return defn


def forget_definition(version_id: uuid.UUID) -> None:
    """Qoralama joyida yangilanganda (§16.1) — shu jarayondagi eski yozuvlar xotiradan tashlanadi."""
    for key in [k for k in _DEFINITIONS if k[0] == version_id]:
        del _DEFINITIONS[key]


def effective_due(node: Node) -> int | None:
    if node.due_in_minutes is not None:
        return node.due_in_minutes
    return DEFAULT_DUE_MINUTES.get(node.type)


def allowed_answer_types(node: Node) -> set[AnswerType]:
    if node.type == NodeType.DAY_END:
        return {AnswerType.TEXT}
    return set(node.answer_types)


def nudge_lead(node: Node, due: int | None) -> int | None:
    """§9.13: dedlayndan necha ish daqiqasi oldin mentor eslatadi (oyna qisqa bo'lsa — yo'q)."""
    if node.type not in ANSWER_TYPES or due is None or due < NUDGE_MIN_WINDOW:
        return None
    return min(NUDGE_MAX_LEAD, due // 3)


def _without_nudge(result: dict | None) -> dict:
    return {k: v for k, v in (result or {}).items() if k != NUDGE_AT}


def _iso(t: datetime | None) -> str | None:
    return t.isoformat() if t else None


def mark_report_due(e: RunEvent, node: Node) -> None:
    if node.type == NodeType.DAY_END and not (e.result or {}).get("report"):
        e.result = {**(e.result or {}), REPORT_DUE: True}


# ── Run yaratish ──────────────────────────────────────────────────────


async def create_run(
    db: AsyncSession,
    user_id: uuid.UUID,
    version: ScenarioVersion,
    now: datetime,
    requested_start: datetime | None = None,
) -> tuple[Run, StartInfo]:
    """§9.2 Q10: istalgan payt boshlanadi; kech boshlansa ogohlantirish. Commit chaqiruvchida."""
    if requested_start is not None:
        if requested_start.tzinfo is None:
            raise Invalid("start_at vaqt zonasi bilan berilishi kerak")
        if requested_start < now - timedelta(minutes=1):
            raise Invalid("start_at o'tgan vaqt bo'lmasin")

    open_run = (await db.execute(
        select(Run.id).where(
            Run.user_id == user_id,
            Run.scenario_version_id == version.id,
            Run.status.in_(OPEN_STATUSES),
        )
    )).first()
    if open_run is not None:
        raise Conflict("Bu ssenariyda tugallanmagan Run bor")

    cal = await load_calendar(db)
    defn = definition_for(version)
    start_at = cal.normalize(max(requested_start or now, now))
    run = Run(
        id=uuid.uuid4(),
        user_id=user_id,
        scenario_version_id=version.id,
        status=RunStatus.SCHEDULED if start_at > now else RunStatus.ACTIVE,
        start_at=start_at,
        ends_at=start_at,  # pastda hisoblanadi
        last_activity_at=now,
        flags=[],
    )
    run.scenario_version = version
    events = [
        RunEvent(
            id=uuid.uuid4(),
            run_id=run.id,
            node_id=n.id,
            status=RunEventStatus.PENDING,
            scheduled_at=cal.schedule(start_at, n.day, n.at),
        )
        for n in defn.nodes
        if n.day is not None
    ]
    run.ends_at = cal.ends_at(max(e.scheduled_at for e in events))
    db.add(run)
    await db.flush()
    db.add_all(events)
    await db.flush()

    day1_ends_at = cal.day_end(start_at, 1)
    warning = None
    if cal.is_late_start(start_at):
        local_end = day1_ends_at.astimezone(cal.tz)
        warning = (
            "Ish kuni 09:00 da boshlanadi. Hozir boshlasangiz, ssenariy jadvali siljiydi: "
            f"1-kun {local_end:%d.%m %H:%M} da tugaydi."
        )
    return run, StartInfo(warning=warning, day1_ends_at=day1_ends_at)


# ── Qulflash ──────────────────────────────────────────────────────────


async def lock_run(db: AsyncSession, run_id: uuid.UUID, user_id: uuid.UUID) -> Run:
    """Egasining Run'i, `FOR UPDATE` bilan. Boshqa foydalanuvchiga — 404 (§9.9)."""
    run = (await db.execute(
        select(Run)
        .where(Run.id == run_id, Run.user_id == user_id)
        .options(selectinload(Run.scenario_version))
        .with_for_update(of=Run)
    )).scalars().first()
    if run is None:
        raise NotFound("Run topilmadi")
    return run


# ── advance ───────────────────────────────────────────────────────────


async def advance(db: AsyncSession, now: datetime, run_id: uuid.UUID | None = None) -> list[Note]:
    """
    `run_id` berilsa — faqat shu Run (API), aks holda ishi bor barcha ochiq
    Run'lar (cron, `SKIP LOCKED`). Commit chaqiruvchida.
    """
    q = select(Run).where(Run.status.in_(OPEN_STATUSES)).options(selectinload(Run.scenario_version))
    if run_id is not None:
        q = q.where(Run.id == run_id).with_for_update(of=Run)
    else:
        due_event = exists(select(RunEvent.id).where(
            RunEvent.run_id == Run.id,
            or_(
                and_(RunEvent.status == RunEventStatus.PENDING, RunEvent.scheduled_at <= now),
                and_(RunEvent.status == RunEventStatus.DELIVERED, RunEvent.due_at <= now),
                # §9.13: mentor eslatmasi vaqti (yozilgach kalit o'chiriladi)
                RunEvent.result[NUDGE_AT].astext.cast(DateTime(timezone=True)) <= now,
            ),
        ))
        q = q.where(or_(
            and_(Run.status == RunStatus.SCHEDULED, Run.start_at <= now),
            Run.ends_at <= now,
            Run.last_activity_at <= now - INACTIVITY_LIMIT,
            due_event,
        )).with_for_update(of=Run, skip_locked=True)

    runs = (await db.execute(q)).scalars().all()
    if not runs:
        return []
    cal = await load_calendar(db)
    notes: list[Note] = []
    for run in runs:
        notes += await advance_run(db, run, now, cal)
    await db.flush()
    return notes


async def advance_run(db: AsyncSession, run: Run, now: datetime, cal: WorkCalendar | None = None) -> list[Note]:
    """Qulflangan bitta Run uchun `advance`."""
    if run.status not in OPEN_STATUSES:
        return []
    cal = cal or await load_calendar(db)
    notes: list[Note] = []
    if run.status == RunStatus.SCHEDULED:
        if run.start_at > now:
            return notes
        run.status = RunStatus.ACTIVE
        notes.append(Note(run.id, "run_status", {"status": RunStatus.ACTIVE.value}))

    state = await RunState.load(db, run, cal)
    expire_at = min(run.ends_at, run.last_activity_at + INACTIVITY_LIMIT)
    # Cron kechiksa ham: avval yonish paytigacha bo'lgan hodisalar tartib bilan
    notes += state.process(horizon=min(now, expire_at), now=now)
    if expire_at <= now:
        notes += state.close(RunStatus.EXPIRED, now)
    else:
        notes += await state.nudge(now)
        notes += state.complete_if_done()
    await db.flush()
    return notes


# ── Bitta Run holati ──────────────────────────────────────────────────


class RunState:
    """Qulflangan Run'ning hodisalari va javoblari xotirada; o'zgarishlar sessiyaga yoziladi."""

    def __init__(
        self,
        db: AsyncSession,
        run: Run,
        cal: WorkCalendar,
        events: list[RunEvent],
        submissions: list[Submission],
        defn: ScenarioDefinition,
    ):
        self.db = db
        self.run = run
        self.cal = cal
        self.defn = defn
        self.order = {n.id: i for i, n in enumerate(defn.nodes)}
        self._chat_seq = 0
        self.events = events
        self.submissions = submissions

    @classmethod
    async def load(cls, db: AsyncSession, run: Run, cal: WorkCalendar) -> RunState:
        events = (await db.execute(select(RunEvent).where(RunEvent.run_id == run.id))).scalars().all()
        subs = (await db.execute(select(Submission).where(Submission.run_id == run.id))).scalars().all()
        # identity map'dan; relationship yuklanmagan bo'lsa ham lazy-load qilinmaydi
        version = await db.get(ScenarioVersion, run.scenario_version_id)
        return cls(db, run, cal, list(events), list(subs), definition_for(version))

    def event(self, node_id: str) -> RunEvent | None:
        return next((e for e in self.events if e.node_id == node_id), None)

    def attempts(self, event: RunEvent) -> list[Submission]:
        return sorted((s for s in self.submissions if s.run_event_id == event.id), key=lambda s: s.attempt)

    # ── Shartlar konteksti ──

    def context(self) -> ConditionContext:
        scores: dict[str, float] = {}
        awaiting: set[str] = set()
        for e in self.events:
            attempts = self.attempts(e)
            if not attempts:
                continue
            if attempts[-1].ai_eval_status in AWAITING_EVAL:
                awaiting.add(e.node_id)
            graded = [
                s for s in attempts
                if s.ai_eval_status == AIEvalStatus.COMPLETED and s.ai_score is not None
            ]
            if graded:
                scores[e.node_id] = graded[-1].ai_score
        return ConditionContext(
            submitted=frozenset(e.node_id for e in self.events if e.status == RunEventStatus.SUBMITTED),
            missed=frozenset(
                e.node_id for e in self.events
                if e.status == RunEventStatus.MISSED or (e.result or {}).get("missed_at")
            ),
            scores=scores,
            awaiting_score=frozenset(awaiting),
            choices={e.node_id: e.choice for e in self.events if e.choice},
            flags=frozenset(self.run.flags or []),
        )

    # ── Vaqt bo'yicha o'tishlar ──

    def process(self, horizon: datetime, now: datetime) -> list[Note]:
        """
        `horizon`gacha vaqti kelgan yetkazish va dedlaynlarni **xronologik**
        tartibda bajaradi: 13:00 dagi shart 13:30 dagi dedlayndan oldin
        tekshiriladi, cron qancha kechiksa ham.
        """
        notes: list[Note] = []
        deferred: set[uuid.UUID] = set()
        while True:
            candidates = []
            for e in self.events:
                if e.id in deferred:
                    continue
                # bir vaqtdagi hodisalar — ssenariydagi tartibda
                order = self.order[e.node_id]
                if e.status == RunEventStatus.PENDING and e.scheduled_at <= horizon:
                    candidates.append((e.scheduled_at, 0, order, e))
                elif e.status == RunEventStatus.DELIVERED and e.due_at is not None and e.due_at <= horizon:
                    candidates.append((e.due_at, 1, order, e))
            if not candidates:
                return notes
            _, kind, _, e = min(candidates, key=lambda c: c[:3])
            if kind == 1:
                notes.append(self._miss(e, e.due_at))
                continue
            node = self.defn.node(e.node_id)
            ctx = self.context()
            if pending_scores(node.when, ctx) and now < e.scheduled_at + SCORE_WAIT:
                deferred.add(e.id)
                continue
            if evaluate(node.when, ctx):
                notes += self._deliver(e, node, now)
            else:
                e.status = RunEventStatus.SKIPPED

    def _deliver(self, e: RunEvent, node: Node, now: datetime) -> list[Note]:
        e.status = RunEventStatus.DELIVERED
        e.delivered_at = now
        due = effective_due(node)
        # §9.2: dedlayn yetkazilgan paytdan — cron kechiksa talaba vaqt yo'qotmaydi
        e.due_at = self.cal.add_work_minutes(now, due) if due else None
        if (lead := nudge_lead(node, due)) and self.defn.mentor is not None:
            e.result = {**(e.result or {}), NUDGE_AT: _iso(self.cal.add_work_minutes(now, due - lead))}
        notes = [Note(self.run.id, "event_delivered", {
            "node_id": node.id, "type": node.type.value, "due_at": _iso(e.due_at),
        })]
        if node.from_ and node.brief:
            # §9.4: skript xabar personaj chatida ham ko'rinadi (generated=false)
            # bir paytda yetkazilgan xabarlar tartibi saqlansin (created_at bo'yicha saralanadi)
            self._chat_seq += 1
            self.db.add(ChatMessage(
                run_id=self.run.id, persona_key=node.from_, sender=ChatSender.PERSONA,
                body=node.brief, generated=False, created_at=now + timedelta(microseconds=self._chat_seq),
            ))
        self.spawn_children(node.id, "delivered", now)
        return notes

    def _miss(self, e: RunEvent, at: datetime) -> Note:
        e.status = RunEventStatus.MISSED
        e.result = {**_without_nudge(e.result), "missed_at": _iso(at)}
        mark_report_due(e, self.defn.node(e.node_id))
        return Note(self.run.id, "event_missed", {"node_id": e.node_id})

    def spawn_children(self, node_id: str, trigger: str, at: datetime) -> None:
        """`after: {node, event, minutes}` node'lari trigger sodir bo'lganda yaratiladi (§9.8)."""
        existing = {e.node_id for e in self.events}
        for n in self.defn.nodes:
            if n.after is None or n.after.node != node_id or n.after.event != trigger or n.id in existing:
                continue
            child = RunEvent(
                id=uuid.uuid4(),
                run_id=self.run.id,
                node_id=n.id,
                status=RunEventStatus.PENDING,
                scheduled_at=self.cal.start_after(at, n.after.minutes),
            )
            self.db.add(child)
            self.events.append(child)

    # ── Mentor eslatmasi (§9.13) ──

    async def nudge(self, now: datetime) -> list[Note]:
        """Vaqti kelgan `nudge_at`: hali topshirilmagan va talaba jim bo'lsa — mentor eslatadi."""
        mentor = self.defn.mentor
        notes: list[Note] = []
        for e in self.events:
            at = (e.result or {}).get(NUDGE_AT)
            if at is None or datetime.fromisoformat(at) > now:
                continue
            result = _without_nudge(e.result)
            if mentor is not None and e.status == RunEventStatus.DELIVERED and not await self._student_wrote_since(e.delivered_at):
                node = self.defn.node(e.node_id)
                title = short_title(node.brief)
                due = e.due_at.astimezone(self.cal.tz).strftime("%H:%M")
                self._chat_seq += 1
                msg = ChatMessage(
                    id=uuid.uuid4(), run_id=self.run.id, persona_key=mentor.key, sender=ChatSender.PERSONA,
                    body=mentor.nudge_text(title, due), generated=False,
                    created_at=now + timedelta(microseconds=self._chat_seq), purpose=CHAT_PURPOSE_NUDGE, node_id=node.id,
                )
                self.db.add(msg)
                result["nudged_at"] = _iso(now)
                notes.append(Note(self.run.id, "chat_message", {"persona_key": mentor.key, "id": str(msg.id)}))
            else:
                result["nudge_skipped"] = _iso(now)
            e.result = result
        return notes

    async def _student_wrote_since(self, since: datetime) -> bool:
        return bool(await self.db.scalar(select(exists().where(
            ChatMessage.run_id == self.run.id,
            ChatMessage.sender == ChatSender.STUDENT,
            ChatMessage.created_at >= since,
        ))))

    # ── Yakunlash ──

    def is_done(self) -> bool:
        """§9.2: oxirgi `day_end` yopilgan, `pending` yo'q, ochiq dedlaynli baholanadigan hodisa yo'q."""
        last = next(
            n for n in self.defn.nodes
            if n.type == NodeType.DAY_END and n.day == self.defn.duration_days
        )
        last_event = self.event(last.id)
        if last_event is None or last_event.status not in (RunEventStatus.SUBMITTED, RunEventStatus.MISSED):
            return False
        for e in self.events:
            if e.status == RunEventStatus.PENDING:
                return False
            if e.status == RunEventStatus.DELIVERED and self.defn.node(e.node_id).is_graded:
                return False
        return True

    def complete_if_done(self) -> list[Note]:
        if self.run.status != RunStatus.ACTIVE or not self.is_done():
            return []
        self.run.status = RunStatus.COMPLETED
        return [Note(self.run.id, "run_status", {"status": RunStatus.COMPLETED.value})]

    def close(self, status: RunStatus, now: datetime) -> list[Note]:
        """`expired`/`abandoned`: `pending` → `skipped`, ochiq baholanadigan hodisa → `missed`."""
        for e in self.events:
            if e.status == RunEventStatus.PENDING:
                e.status = RunEventStatus.SKIPPED
            elif e.status == RunEventStatus.DELIVERED and self.defn.node(e.node_id).is_graded:
                self._miss(e, now)
        self.run.status = status
        return [Note(self.run.id, "run_status", {"status": status.value})]

    # ── Talaba harakatlari ──

    def open_event(self, node_id: str) -> tuple[RunEvent, Node]:
        if self.run.status != RunStatus.ACTIVE:
            raise Conflict("Run faol emas")
        e = self.event(node_id)
        if e is None or e.status in (RunEventStatus.PENDING, RunEventStatus.SKIPPED):
            raise NotFound("Hodisa topilmadi")
        return e, self.defn.node(node_id)


async def submit_answer(
    db: AsyncSession, run: Run, node_id: str, answer: Answer, now: datetime
) -> tuple[Submission, list[Note]]:
    """
    Task/incident/day_end javobi (§9.0 Q11): ko'pi bilan `max_attempts`,
    dedlayndan keyin — `late=true`. Baholash arq job'da (`ai_eval_status=pending`).
    Run qulflangan va `advance_run` qilingan bo'lishi kerak.
    """
    state = await RunState.load(db, run, await load_calendar(db))
    e, node = state.open_event(node_id)
    if node.type not in ANSWER_TYPES and node.type != NodeType.DAY_END:
        raise Invalid("Bu hodisaga javob yuborilmaydi")

    kinds = answer.kinds()
    if not kinds:
        raise Invalid("Javob bo'sh")
    allowed = allowed_answer_types(node)
    if extra := kinds - allowed:
        raise Invalid(f"Ruxsat etilmagan javob turi: {sorted(k.value for k in extra)}")
    content = answer.content()
    if len(content) > MAX_CONTENT_LENGTH:
        raise Invalid(f"Javob {MAX_CONTENT_LENGTH} belgidan oshmasin")
    if answer.link_url and not answer.link_url.startswith(("https://", "http://")):
        raise Invalid("Havola http(s):// bilan boshlansin")
    if answer.file_id is not None:
        f = await db.get(UploadedFile, answer.file_id)
        if f is None or f.owner_user_id != run.user_id or f.run_id not in (None, run.id):
            raise Invalid("Fayl topilmadi")

    previous = state.attempts(e)
    if len(previous) >= node.max_attempts:
        raise Conflict(f"Urinishlar tugadi ({node.max_attempts})")

    late = e.due_at is not None and now > e.due_at
    sub = Submission(
        id=uuid.uuid4(),
        run_id=run.id,
        run_event_id=e.id,
        user_id=run.user_id,
        attempt=len(previous) + 1,
        late=late,
        content=content,
        file_id=answer.file_id,
        link_url=answer.link_url,
        ai_eval_status=AIEvalStatus.PENDING,
        submitted_at=now,
    )
    db.add(sub)
    state.submissions.append(sub)
    e.status = RunEventStatus.SUBMITTED
    e.result = _without_nudge(e.result) or None
    mark_report_due(e, node)
    if not previous:
        state.spawn_children(node_id, "submitted", now)
    notes = [Note(run.id, "event_submitted", {"node_id": node_id, "attempt": sub.attempt, "late": late})]
    notes += state.complete_if_done()
    await db.flush()
    return sub, notes


async def decide(
    db: AsyncSession, run: Run, node_id: str, option_key: str, now: datetime
) -> tuple[Submission, list[Note]]:
    """`decision` — bir marta; variant bahosi va `flag` darhol (AI kerak emas)."""
    state = await RunState.load(db, run, await load_calendar(db))
    e, node = state.open_event(node_id)
    if node.type != NodeType.DECISION:
        raise Invalid("Bu hodisa qaror emas")
    if e.choice is not None:
        raise Conflict("Qaror allaqachon qabul qilingan")
    option = next((o for o in node.options if o.key == option_key), None)
    if option is None:
        raise Invalid("Bunday variant yo'q")

    late = e.due_at is not None and now > e.due_at
    score = DECISION_SCORES[option.grade] * ((1 - node.late_penalty) if late else 1)
    e.choice = option.key
    e.status = RunEventStatus.SUBMITTED
    if option.flag and option.flag not in (run.flags or []):
        run.flags = [*(run.flags or []), option.flag]
    sub = Submission(
        id=uuid.uuid4(),
        run_id=run.id,
        run_event_id=e.id,
        user_id=run.user_id,
        attempt=1,
        late=late,
        content=option.label,
        ai_score=round(score, 1),
        ai_eval_status=AIEvalStatus.COMPLETED,
        submitted_at=now,
        evaluated_at=now,
    )
    db.add(sub)
    state.submissions.append(sub)
    state.spawn_children(node_id, "submitted", now)
    notes = [Note(run.id, "event_submitted", {"node_id": node_id, "attempt": 1, "late": late})]
    notes += state.complete_if_done()
    await db.flush()
    return sub, notes


@dataclass(frozen=True)
class HintInfo:
    hint: str
    hints_used: int
    hints_left: int
    penalty: float          # shu task'ning maksimal balidan jami ayirma (0..1)


async def take_hint(db: AsyncSession, run: Run, node_id: str, now: datetime) -> tuple[HintInfo, list[Note]]:
    """
    §9.4: navbatdagi hint; har biri task maksimal balini `hint_penalty`ga
    kamaytiradi. Mentor bo'lsa hint uning chatiga ham yoziladi.
    """
    state = await RunState.load(db, run, await load_calendar(db))
    e, node = state.open_event(node_id)
    if not node.hints:
        raise NotFound("Bu task uchun hint yo'q")
    if e.hints_used >= len(node.hints):
        raise Conflict("Hintlar tugadi")
    hint = node.hints[e.hints_used]
    e.hints_used += 1
    mentor = next((p for p in state.defn.personas if p.kind.value == "mentor"), None)
    if mentor is not None:
        db.add(ChatMessage(
            run_id=run.id, persona_key=mentor.key, sender=ChatSender.PERSONA,
            body=hint, generated=False, created_at=now,
        ))
    await db.flush()
    info = HintInfo(
        hint=hint,
        hints_used=e.hints_used,
        hints_left=len(node.hints) - e.hints_used,
        penalty=round(min(1.0, node.hint_penalty * e.hints_used), 3),
    )
    return info, [Note(run.id, "hint", {"node_id": node_id, "hints_used": e.hints_used})]


async def abandon(db: AsyncSession, run: Run, now: datetime) -> list[Note]:
    if run.status not in OPEN_STATUSES:
        raise Conflict("Run allaqachon yopilgan")
    state = await RunState.load(db, run, await load_calendar(db))
    notes = state.close(RunStatus.ABANDONED, now)
    await db.flush()
    return notes
