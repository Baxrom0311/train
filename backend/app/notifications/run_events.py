"""
Run hodisalaridan bildirishnoma (CONTRACT.md §15.2): dvigatel `Note`lari va
dedlayn eslatmasi. Dvigatel jadvallarini faqat o'qiydi.
"""
import uuid
from datetime import datetime, timedelta

from sqlalchemy import and_, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import NodeType, RunEventStatus, RunStatus
from app.models.notification import Notification
from app.models.scenario import Run, RunEvent, Scenario, ScenarioVersion
from app.notifications.kinds import Kind
from app.notifications.service import notify
from app.scenario.engine import Note, definition_for
from app.scenario.schema import short_title

DEADLINE_LEAD = timedelta(minutes=30)
_DELIVERED = {NodeType.TASK.value, NodeType.INCIDENT.value, NodeType.DECISION.value}


def _iso(t: datetime | None) -> str | None:
    return t.isoformat() if t else None


async def _run_titles(db: AsyncSession, run_ids: set[uuid.UUID]) -> dict[uuid.UUID, tuple[Run, dict[str, str]]]:
    """Run va uning node sarlavhalari (`short_title(brief)`)."""
    rows = (await db.execute(
        select(Run, ScenarioVersion).join(ScenarioVersion, Run.scenario_version_id == ScenarioVersion.id)
        .where(Run.id.in_(run_ids))
    )).all()
    return {
        run.id: (run, {n.id: short_title(n.brief) for n in definition_for(version).nodes})
        for run, version in rows
    }


async def from_notes(db: AsyncSession, notes: list[Note], now: datetime) -> None:
    """`event_delivered` (task/incident/decision) → `task_delivered`. Chaqiruvchi commit qiladi."""
    delivered = [n for n in notes if n.type == "event_delivered" and n.data.get("type") in _DELIVERED]
    if not delivered:
        return
    runs = await _run_titles(db, {n.run_id for n in delivered})
    for note in delivered:
        run, titles = runs[note.run_id]
        node_id = note.data["node_id"]
        await notify(
            db, run.user_id, Kind.TASK_DELIVERED,
            {"run_id": str(run.id), "node_id": node_id, "type": note.data["type"],
             "title": titles.get(node_id, ""), "due_at": note.data.get("due_at")},
            link=f"/runs/{run.id}", key=f"event:{run.id}:{node_id}:delivered", at=now,
        )


async def deadline_reminders(db: AsyncSession, now: datetime) -> int:
    """Topshirilmagan, dedlayniga ≤ 30 daqiqa qolgan hodisalar — bittadan eslatma."""
    already = exists().where(and_(
        Notification.user_id == Run.user_id,
        Notification.dedupe_key == func.concat("event:", RunEvent.run_id, ":", RunEvent.node_id, ":deadline"),
    ))
    rows = (await db.execute(
        select(RunEvent, Run.user_id)
        .join(Run, Run.id == RunEvent.run_id)
        .where(
            Run.status == RunStatus.ACTIVE,
            RunEvent.status == RunEventStatus.DELIVERED,
            RunEvent.due_at > now,
            RunEvent.due_at <= now + DEADLINE_LEAD,
            ~already,
        )
    )).all()
    if not rows:
        return 0
    runs = await _run_titles(db, {e.run_id for e, _ in rows})
    for e, user_id in rows:
        await notify(
            db, user_id, Kind.DEADLINE_SOON,
            {"run_id": str(e.run_id), "node_id": e.node_id, "title": runs[e.run_id][1].get(e.node_id, ""),
             "due_at": _iso(e.due_at)},
            link=f"/runs/{e.run_id}", key=f"event:{e.run_id}:{e.node_id}:deadline", at=now,
        )
    return len(rows)


async def review_posted(
    db: AsyncSession, run: Run, node_id: str, title: str, mentor: str, submission_id: uuid.UUID, now: datetime,
) -> None:
    """Mentor izohi yozildi (§9.13) → `mentor_review`."""
    await notify(
        db, run.user_id, Kind.MENTOR_REVIEW,
        {"run_id": str(run.id), "node_id": node_id, "title": title, "mentor": mentor},
        link=f"/runs/{run.id}", key=f"review:{submission_id}", at=now,
    )


async def report_ready(db: AsyncSession, run: Run, code: str | None, now: datetime) -> None:
    """Yakuniy hisobot yozildi → `report_ready` (sertifikat bo'lsa — kodi bilan)."""
    title = await db.scalar(
        select(Scenario.title).join(ScenarioVersion, ScenarioVersion.scenario_id == Scenario.id)
        .where(ScenarioVersion.id == run.scenario_version_id)
    )
    await notify(
        db, run.user_id, Kind.REPORT_READY,
        {"run_id": str(run.id), "scenario_title": title, "certificate": code is not None, "code": code},
        link=f"/runs/{run.id}/report", key=f"final:{run.id}", at=now,
    )
