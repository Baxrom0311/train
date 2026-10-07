"""
Kunlik va yakuniy hisobotlar (CONTRACT.md §9.6).

- **Kunlik** — kun yakuni (`day_end`) topshirilgan yoki o'tkazib yuborilgan
  paytda: shu kun task'lari natijasi + AI'ning qisqa xulosasi →
  `run_events.result["report"]`.
- **Yakuniy** — Run `completed` yoki `expired` bo'lganda: task natijalari,
  kompetensiya ballari (0–100) → `runs.final_report`, `runs.competency_scores`.
  `expired` — `"incomplete": true`, sertifikat yo'q; `completed` — sertifikat (§13.1).

Ballar faqat kodda hisoblanadi; AI faqat matn va `initiative` bahosini beradi
(AI ishlamasa — hisobot matnsiz, `initiative` task'lardan). Baholash hali
tugamagan javoblar 15 daqiqagacha kutiladi, keyin hisobotga kirmaydi.

Hisobot yozilishi kerak bo'lgan joylarni cron topadi (`pending_*`) va
job'larni navbatga qo'yadi — API va dvigatel arq'ga bog'liq emas.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.reports import final_report as ai_final_report, summarize_day
from app.credentials.issue import issue_for_run
from app.notifications.run_events import report_ready
from app.models.enums import (
    AIEvalStatus,
    ChatSender,
    Competency,
    NodeType,
    RunEventStatus,
    RunStatus,
)
from app.models.scenario import ChatMessage, Run, RunEvent, ScenarioVersion
from app.models.simulation import Submission
from app.scenario.engine import REPORT_DUE, definition_for
from app.scenario.schema import Node, ScenarioDefinition

EVAL_WAIT = timedelta(minutes=15)
AWAITING = (AIEvalStatus.PENDING, AIEvalStatus.QUEUED_RETRY)
CLOSED = (RunStatus.COMPLETED, RunStatus.EXPIRED)


@dataclass
class TaskResult:
    node_id: str
    type: str
    title: str
    day: int
    status: str
    score: float | None          # yakuniy (jarimali) ball; hisobga kirmasa None
    counted: bool
    attempts: int
    late: bool
    score_history: list[float] = field(default_factory=list)
    competencies: list[str] = field(default_factory=list)
    weight: float = 1.0

    def public(self) -> dict:
        d = asdict(self)
        d.pop("counted")
        d.pop("weight")
        return d


def task_title(node: Node) -> str:
    return (node.brief or "Kun yakuni hisoboti").split("\n")[0][:100]


def node_score(event: RunEvent, attempts: list[Submission]) -> tuple[float | None, bool]:
    """(ball, hisobga kiradimi). Topshirilmay o'tkazib yuborilgan — 0; baho yo'q — kirmaydi."""
    graded = [s.ai_score for s in attempts if s.ai_eval_status == AIEvalStatus.COMPLETED and s.ai_score is not None]
    if graded:
        return graded[-1], True
    if not attempts and event.status == RunEventStatus.MISSED:
        return 0.0, True
    return None, False


def _day_bounds(defn: ScenarioDefinition, events: dict[str, RunEvent]) -> list[datetime | None]:
    """Har kunning `day_end` vaqti — nisbiy (`after`) node qaysi kunga tegishli ekanini aniqlash uchun."""
    ends: list[datetime | None] = []
    for day in range(1, defn.duration_days + 1):
        node = next(n for n in defn.nodes if n.type == NodeType.DAY_END and n.day == day)
        ends.append(events[node.id].scheduled_at if node.id in events else None)
    return ends


def _event_day(e: RunEvent, bounds: list[datetime | None]) -> int:
    at = e.delivered_at or e.scheduled_at
    for day, end in enumerate(bounds, start=1):
        if end is None or at <= end:
            return day
    return len(bounds)


async def load_results(db: AsyncSession, run: Run) -> tuple[ScenarioDefinition, list[TaskResult], list[Submission]]:
    version = await db.get(ScenarioVersion, run.scenario_version_id)
    defn = definition_for(version)
    events = {
        e.node_id: e for e in (await db.execute(select(RunEvent).where(RunEvent.run_id == run.id))).scalars()
    }
    subs = list((await db.execute(
        select(Submission).where(Submission.run_id == run.id).order_by(Submission.attempt)
    )).scalars())
    by_event: dict[uuid.UUID, list[Submission]] = {}
    for s in subs:
        by_event.setdefault(s.run_event_id, []).append(s)

    bounds = _day_bounds(defn, events)
    results = []
    for node in defn.nodes:
        e = events.get(node.id)
        if e is None or not node.is_graded or e.status in (RunEventStatus.PENDING, RunEventStatus.SKIPPED):
            continue
        attempts = by_event.get(e.id, [])
        score, counted = node_score(e, attempts)
        results.append(TaskResult(
            node_id=node.id,
            type=node.type.value,
            title=task_title(node),
            day=node.day or _event_day(e, bounds),
            status=e.status.value,
            score=score,
            counted=counted,
            attempts=len(attempts),
            late=any(s.late for s in attempts),
            score_history=[s.ai_score for s in attempts if s.ai_score is not None],
            competencies=[c.value for c in node.competencies],
            weight=node.weight,
        ))
    return defn, results, subs


def on_time_rate(results: list[TaskResult]) -> float | None:
    graded = [r for r in results if r.status in (RunEventStatus.SUBMITTED.value, RunEventStatus.MISSED.value)]
    if not graded:
        return None
    on_time = [r for r in graded if r.status == RunEventStatus.SUBMITTED.value and not r.late]
    return round(100 * len(on_time) / len(graded), 1)


def _weighted(rs: list[TaskResult]) -> float | None:
    rs = [r for r in rs if r.counted]
    total = sum(r.weight for r in rs)
    return round(sum(r.score * r.weight for r in rs) / total, 1) if total else None


def competency_scores(results: list[TaskResult], initiative: float | None = None) -> dict[str, float]:
    """
    Har kompetensiya — shu kompetensiya belgilangan task'lar ballining
    og'irlikli o'rtachasi. Qo'shimcha: `day_end` → `communication`;
    `time_management` — o'z vaqtida topshirish ulushi bilan o'rtacha;
    `initiative` — AI transkript bahosi (bo'lsa). Ma'lumot yo'q — kalit yo'q.
    """
    out: dict[str, float] = {}
    for c in Competency:
        tagged = [
            r for r in results
            if c.value in r.competencies or (c == Competency.COMMUNICATION and r.type == NodeType.DAY_END.value)
        ]
        value = _weighted(tagged)
        if c == Competency.TIME_MANAGEMENT:
            rate = on_time_rate(results)
            if rate is not None:
                value = rate if value is None else round((value + rate) / 2, 1)
        if c == Competency.INITIATIVE and initiative is not None:
            value = round(initiative, 1) if value is None else round((value + initiative) / 2, 1)
        if value is not None:
            out[c.value] = value
    return out


def _evals_settled(subs: list[Submission], now: datetime) -> bool:
    """Baholanayotgan javob yo'q, yoki eng so'nggisi 15 daqiqadan oldin topshirilgan."""
    waiting = [s for s in subs if s.ai_eval_status in AWAITING]
    return not waiting or now - max(s.submitted_at for s in waiting) >= EVAL_WAIT


# ── Kunlik ────────────────────────────────────────────────────────────


async def write_day_report(
    db: AsyncSession, run_id: uuid.UUID, node_id: str, now: datetime, *, summarize=None
) -> bool:
    """Yozildimi (yoki allaqachon bor). `False` — hali erta, cron keyinroq qayta chaqiradi."""
    summarize = summarize or summarize_day
    run = await db.get(Run, run_id)
    event = (await db.execute(
        select(RunEvent).where(RunEvent.run_id == run_id, RunEvent.node_id == node_id)
    )).scalars().first()
    if run is None or event is None or (event.result or {}).get("report"):
        return True
    if event.status not in (RunEventStatus.SUBMITTED, RunEventStatus.MISSED):
        return False

    defn, results, subs = await load_results(db, run)
    day = defn.node(node_id).day
    day_results = [r for r in results if r.day == day]
    if not _evals_settled(subs, now):
        return False

    day_end_sub = next(
        (s for s in reversed(subs) if s.run_event_id == event.id), None
    )
    tasks = [r.public() for r in day_results]
    summary = await summarize(day, tasks, day_end_sub.content if day_end_sub else None)
    report = {
        "day": day,
        "generated_at": now.isoformat(),
        "tasks": tasks,
        "average_score": _weighted(day_results),
        "on_time_rate": on_time_rate(day_results),
        "summary": summary.model_dump() if summary else None,
    }
    await db.refresh(event, with_for_update=True)
    if not (event.result or {}).get("report"):
        event.result = {**(event.result or {}), "report": report, REPORT_DUE: False}
    await db.commit()
    return True


# ── Yakuniy ───────────────────────────────────────────────────────────


async def write_final_report(db: AsyncSession, run_id: uuid.UUID, now: datetime, *, summarize=None) -> bool:
    summarize = summarize or ai_final_report
    run = await db.get(Run, run_id)
    if run is None or run.final_report is not None:
        return True
    if run.status not in CLOSED:
        return False
    defn, results, subs = await load_results(db, run)
    if not _evals_settled(subs, now):
        return False

    base = competency_scores(results)
    messages = (await db.execute(
        select(ChatMessage.body)
        .where(ChatMessage.run_id == run.id, ChatMessage.sender == ChatSender.STUDENT)
        .order_by(ChatMessage.created_at)
    )).scalars().all()
    completed = run.status == RunStatus.COMPLETED
    tasks = [r.public() for r in results]
    summary = await summarize(tasks, base, [m for m in messages if m], completed)
    scores = competency_scores(results, initiative=summary.initiative_score if summary else None)

    report = {
        "generated_at": now.isoformat(),
        "incomplete": not completed,
        "certificate": completed,
        "overall_score": _weighted(results),
        "on_time_rate": on_time_rate(results),
        "competency_scores": scores,
        "tasks": tasks,
        "summary": summary.model_dump() if summary else None,
    }
    await db.refresh(run, with_for_update=True)
    if run.final_report is None:
        run.final_report = report
        run.competency_scores = scores
        code = await issue_for_run(db, run)   # §13.1 — shu tranzaksiyada
        await report_ready(db, run, code, now)   # §15.2
    await db.commit()
    return True


# ── Cron uchun: nima yozilishi kerak ─────────────────────────────────


async def pending_day_reports(db: AsyncSession) -> list[tuple[uuid.UUID, str]]:
    rows = (await db.execute(
        select(RunEvent.run_id, RunEvent.node_id).where(RunEvent.result.contains({REPORT_DUE: True}))
    )).all()
    return [(r[0], r[1]) for r in rows]


async def pending_final_reports(db: AsyncSession) -> list[uuid.UUID]:
    return list((await db.execute(
        select(Run.id).where(Run.status.in_(CLOSED), Run.final_report.is_(None))
    )).scalars())
