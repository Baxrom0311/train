"""
Run hodisalaridan bildirishnoma (CONTRACT.md §15.2): dvigatel `Note`lari va
dedlayn eslatmasi. Dvigatel jadvallarini faqat o'qiydi.

Jamoaviy Run'da (§29.5) vazifa va dedlayn — rol egasiga (umumiy hodisa —
barcha faol a'zolarga), mentor izohi — topshirgan a'zoga, yakuniy hisobot —
barcha faol a'zolarga.
"""
import uuid
from datetime import datetime, timedelta

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import NodeType, RunEventStatus, RunStatus
from app.models.notification import Notification
from app.models.scenario import Run, RunEvent, RunTeamMember, Scenario, ScenarioVersion
from app.notifications.kinds import Kind
from app.notifications.service import notify
from app.scenario.engine import Note, definition_for
from app.scenario.schema import ScenarioDefinition, short_title
from app.scenario.team import TeamView, run_recipients, team_view

DEADLINE_LEAD = timedelta(minutes=30)
_DELIVERED = {NodeType.TASK.value, NodeType.INCIDENT.value, NodeType.DECISION.value}


def _iso(t: datetime | None) -> str | None:
    return t.isoformat() if t else None


class _RunInfo:
    """Run, ssenariy ta'rifi va (jamoaviy bo'lsa) jamoa — bildirishnoma qabul qiluvchilari uchun."""

    def __init__(self, run: Run, defn: ScenarioDefinition, team: TeamView | None):
        self.run = run
        self.defn = defn
        self.team = team

    def title(self, node_id: str) -> str:
        return next((short_title(n.brief) for n in self.defn.nodes if n.id == node_id), "")

    def recipients(self, node_id: str) -> list[uuid.UUID]:
        if self.team is None:
            return [self.run.user_id]
        return self.team.recipients(next((n for n in self.defn.nodes if n.id == node_id), None))


async def _runs(db: AsyncSession, run_ids: set[uuid.UUID]) -> dict[uuid.UUID, _RunInfo]:
    rows = (await db.execute(
        select(Run, ScenarioVersion).join(ScenarioVersion, Run.scenario_version_id == ScenarioVersion.id)
        .where(Run.id.in_(run_ids))
    )).all()
    out = {}
    for run, version in rows:
        defn = definition_for(version)
        out[run.id] = _RunInfo(run, defn, await team_view(db, run, defn))
    return out


async def from_notes(db: AsyncSession, notes: list[Note], now: datetime) -> None:
    """`event_delivered` (task/incident/decision) → `task_delivered`. Chaqiruvchi commit qiladi."""
    delivered = [n for n in notes if n.type == "event_delivered" and n.data.get("type") in _DELIVERED]
    if not delivered:
        return
    runs = await _runs(db, {n.run_id for n in delivered})
    for note in delivered:
        info = runs[note.run_id]
        node_id = note.data["node_id"]
        for user_id in info.recipients(node_id):
            await notify(
                db, user_id, Kind.TASK_DELIVERED,
                {"run_id": str(info.run.id), "node_id": node_id, "type": note.data["type"],
                 "title": info.title(node_id), "due_at": note.data.get("due_at")},
                link=f"/runs/{info.run.id}?event={node_id}", key=f"event:{info.run.id}:{node_id}:delivered", at=now,
            )


async def deadline_reminders(db: AsyncSession, now: datetime) -> int:
    """Topshirilmagan, dedlayniga ≤ 30 daqiqa qolgan hodisalar — bittadan eslatma."""
    # Run egasi yoki jamoa a'zolaridan biriga yozilgan bo'lsa — hodisa ko'rib chiqilgan
    already = exists().where(and_(
        or_(
            Notification.user_id == Run.user_id,
            Notification.user_id.in_(select(RunTeamMember.user_id).where(RunTeamMember.team_id == Run.team_id)),
        ),
        Notification.dedupe_key == func.concat("event:", RunEvent.run_id, ":", RunEvent.node_id, ":deadline"),
    ))
    events = (await db.execute(
        select(RunEvent)
        .join(Run, Run.id == RunEvent.run_id)
        .where(
            Run.status == RunStatus.ACTIVE,
            RunEvent.status == RunEventStatus.DELIVERED,
            RunEvent.due_at > now,
            RunEvent.due_at <= now + DEADLINE_LEAD,
            ~already,
        )
    )).scalars().all()
    if not events:
        return 0
    runs = await _runs(db, {e.run_id for e in events})
    for e in events:
        info = runs[e.run_id]
        for user_id in info.recipients(e.node_id):
            await notify(
                db, user_id, Kind.DEADLINE_SOON,
                {"run_id": str(e.run_id), "node_id": e.node_id, "title": info.title(e.node_id),
                 "due_at": _iso(e.due_at)},
                link=f"/runs/{e.run_id}?event={e.node_id}", key=f"event:{e.run_id}:{e.node_id}:deadline", at=now,
            )
    return len(events)


async def review_posted(
    db: AsyncSession, run: Run, node_id: str, title: str, mentor: str, submission_id: uuid.UUID, now: datetime,
    recipient: uuid.UUID | None = None,
) -> None:
    """Mentor izohi yozildi (§9.13) → `mentor_review`; jamoaviy Run'da — topshirgan a'zoga (§29.5)."""
    await notify(
        db, recipient or run.user_id, Kind.MENTOR_REVIEW,
        {"run_id": str(run.id), "node_id": node_id, "title": title, "mentor": mentor},
        link=f"/runs/{run.id}?event={node_id}", key=f"review:{submission_id}", at=now,
    )


async def report_ready(db: AsyncSession, run: Run, code: str | None, now: datetime) -> None:
    """Yakuniy hisobot yozildi → `report_ready` (sertifikat bo'lsa — kodi bilan)."""
    title = await db.scalar(
        select(Scenario.title).join(ScenarioVersion, ScenarioVersion.scenario_id == Scenario.id)
        .where(ScenarioVersion.id == run.scenario_version_id)
    )
    for user_id in await run_recipients(db, run):
        await notify(
            db, user_id, Kind.REPORT_READY,
            {"run_id": str(run.id), "scenario_title": title, "certificate": code is not None, "code": code},
            link=f"/runs/{run.id}/report", key=f"final:{run.id}", at=now,
        )
