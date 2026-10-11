"""Jamoaviy Run lobbysidan bildirishnoma (CONTRACT.md §29.5). Chaqiruvchi commit qiladi."""
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scenario import Run, RunTeam, Scenario
from app.notifications.kinds import Kind
from app.notifications.service import notify


async def _scenario_title(db: AsyncSession, team: RunTeam) -> str:
    return await db.scalar(select(Scenario.title).where(Scenario.id == team.scenario_id)) or ""


async def team_joined(db: AsyncSession, team: RunTeam, member: str, member_id: uuid.UUID, now: datetime) -> None:
    await notify(
        db, team.captain_id, Kind.TEAM_JOINED,
        {"team_id": str(team.id), "member": member, "scenario": await _scenario_title(db, team)},
        link=f"/teams/{team.id}", key=f"team:{team.id}:joined:{member_id}", at=now,
    )


async def team_started(
    db: AsyncSession, team: RunTeam, run: Run, captain: str, roles: dict[uuid.UUID, list[str]], now: datetime,
) -> None:
    """Kapitandan boshqa a'zolarga; `roles` — har a'zoning rol nomlari."""
    title = await _scenario_title(db, team)
    for user_id, titles in roles.items():
        if user_id == team.captain_id:
            continue
        await notify(
            db, user_id, Kind.TEAM_STARTED,
            {"run_id": str(run.id), "scenario": title, "captain": captain,
             "start_at": run.start_at.isoformat(), "roles": titles},
            link=f"/runs/{run.id}", key=f"team:{team.id}:started", at=now,
        )
