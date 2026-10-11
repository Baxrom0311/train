"""
Jamoaviy Run lobbysi (CONTRACT.md §29.2, §29.6, Modul 9).

Kirgan faol foydalanuvchi (Run kabi — alohida ruxsat yo'q). Jamoani faqat
uning a'zolari ko'radi (boshqalarga 404); taklif kodi bo'yicha qisqa
ko'rinish — havolani olgan har kimga. O'zgartiruvchi so'rovlar jamoa
qatorini qulflaydi (`scenario/team.py`).
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.runs import RunCreatedOut, ScenarioBrief, _detail, _engine_error, get_now
from app.api.scenarios import TeamRolePublic, published_version
from app.core.deps import get_current_active_user
from app.database import get_db
from app.models.scenario import TEAM_FORMING, Run, RunTeam, RunTeamMember, Scenario, ScenarioVersion
from app.models.user import User
from app.scenario import notify
from app.scenario.engine import EngineError, advance_run
from app.scenario.team import (
    INVITE_TTL,
    claim_role,
    create_team,
    disband,
    expires_at,
    join_team,
    leave_team,
    lock_team,
    normalize_invite,
    seat_order,
    remove_member,
    start_team,
    team_spec,
    team_state,
)

router = APIRouter(tags=["teams"])


# ── Sxemalar ──────────────────────────────────────────────────────────


class TeamCreate(BaseModel):
    scenario_id: uuid.UUID


class RoleClaim(BaseModel):
    role: str | None = Field(default=None, max_length=64)


class TeamStart(BaseModel):
    start_at: datetime | None = None


class LobbyMemberOut(BaseModel):
    user_id: uuid.UUID
    name: str
    role: str | None
    is_captain: bool
    joined_at: datetime


class TeamOut(BaseModel):
    id: uuid.UUID
    scenario: ScenarioBrief
    status: str
    state: str                    # forming | expired | started | disbanded
    invite_code: str
    expires_at: datetime
    captain_id: uuid.UUID
    is_captain: bool
    min_size: int
    roles: list[TeamRolePublic]
    members: list[LobbyMemberOut]
    run_id: uuid.UUID | None
    created_at: datetime


class TeamInviteOut(BaseModel):
    """Taklif havolasi bo'yicha — a'zo bo'lmaganga ham (ism faqat kapitanniki)."""
    id: uuid.UUID
    scenario: ScenarioBrief
    state: str
    captain_name: str
    min_size: int
    roles: list[TeamRolePublic]
    taken_roles: list[str]
    members: int
    expires_at: datetime
    is_member: bool


# ── Yordamchilar ──────────────────────────────────────────────────────


async def _scenario(db: AsyncSession, team: RunTeam) -> tuple[ScenarioBrief, ScenarioVersion]:
    scenario = await db.get(Scenario, team.scenario_id)
    version = await db.get(ScenarioVersion, team.scenario_version_id)
    brief = ScenarioBrief(
        id=scenario.id, slug=scenario.slug, title=scenario.title, sector=scenario.sector,
        company_name=scenario.company_name, duration_days=scenario.duration_days,
    )
    return brief, version


async def _members(db: AsyncSession, team: RunTeam) -> list[tuple[RunTeamMember, str]]:
    return list((await db.execute(
        select(RunTeamMember, User.full_name)
        .join(User, User.id == RunTeamMember.user_id)
        .where(RunTeamMember.team_id == team.id)
        .order_by(*seat_order(team.captain_id))
    )).all())


async def _out(db: AsyncSession, team: RunTeam, user: User, now: datetime) -> TeamOut:
    brief, version = await _scenario(db, team)
    spec = team_spec(version)
    run_id = await db.scalar(select(Run.id).where(Run.team_id == team.id))
    return TeamOut(
        id=team.id,
        scenario=brief,
        status=team.status,
        state=team_state(team, now),
        invite_code=team.invite_code,
        expires_at=expires_at(team),
        captain_id=team.captain_id,
        is_captain=team.captain_id == user.id,
        min_size=spec.min_size,
        roles=[TeamRolePublic(key=r.key, title=r.title, summary=r.summary) for r in spec.roles],
        members=[
            LobbyMemberOut(user_id=m.user_id, name=name, role=m.role, is_captain=m.user_id == team.captain_id,
                           joined_at=m.joined_at)
            for m, name in await _members(db, team)
        ],
        run_id=run_id,
        created_at=team.created_at,
    )


async def _member_team(db: AsyncSession, team_id: uuid.UUID, user: User, *, lock: bool = False) -> RunTeam:
    """A'zo bo'lmaganga 404. `lock` — o'zgartirishdan oldin jamoa qatori qulflanadi."""
    try:
        team = await lock_team(db, team_id) if lock else await db.get(RunTeam, team_id)
    except EngineError as exc:
        raise _engine_error(exc)
    if team is None or await db.get(RunTeamMember, (team.id, user.id)) is None:
        raise HTTPException(status_code=404, detail="Jamoa topilmadi")
    return team


async def _by_code(db: AsyncSession, code: str, *, lock: bool = False) -> RunTeam:
    q = select(RunTeam).where(RunTeam.invite_code == normalize_invite(code))
    if lock:
        q = q.with_for_update()
    team = (await db.execute(q)).scalars().first()
    if team is None:
        raise HTTPException(status_code=404, detail="Taklif topilmadi")
    return team


async def _apply(db: AsyncSession, op) -> None:
    """Lobby amali: xato — rollback va HTTP kod; parallel band qilish (UNIQUE) — 409."""
    try:
        await op
        await db.commit()
    except EngineError as exc:
        await db.rollback()
        raise _engine_error(exc)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Holat o'zgardi — sahifani yangilang")


# ── Endpointlar ───────────────────────────────────────────────────────


@router.post("/teams", response_model=TeamOut, status_code=status.HTTP_201_CREATED)
async def create(
    body: TeamCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
    now: datetime = Depends(get_now),
):
    # katalog ssenariysi (§26 kompaniya ssenariylari — 404)
    _, version = await published_version(db, body.scenario_id)
    try:
        team = await create_team(db, user, version, now)
        await db.commit()
    except EngineError as exc:
        await db.rollback()
        raise _engine_error(exc)
    return await _out(db, team, user, now)


@router.get("/teams/my", response_model=list[TeamOut])
async def my_teams(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
    now: datetime = Depends(get_now),
):
    """Yig'ilayotgan (yonmagan) jamoalar; boshlanganlari — `GET /runs/my`da."""
    teams = (await db.execute(
        select(RunTeam)
        .join(RunTeamMember, RunTeamMember.team_id == RunTeam.id)
        .where(
            RunTeamMember.user_id == user.id,
            RunTeam.status == TEAM_FORMING,
            RunTeam.created_at > now - INVITE_TTL,
        )
        .order_by(RunTeam.created_at.desc())
    )).scalars().all()
    return [await _out(db, t, user, now) for t in teams]


@router.get("/teams/invite/{code}", response_model=TeamInviteOut)
async def invite(
    code: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
    now: datetime = Depends(get_now),
):
    team = await _by_code(db, code)
    brief, version = await _scenario(db, team)
    spec = team_spec(version)
    members = await _members(db, team)
    captain = next(name for m, name in members if m.user_id == team.captain_id)
    return TeamInviteOut(
        id=team.id,
        scenario=brief,
        state=team_state(team, now),
        captain_name=captain,
        min_size=spec.min_size,
        roles=[TeamRolePublic(key=r.key, title=r.title, summary=r.summary) for r in spec.roles],
        taken_roles=[m.role for m, _ in members if m.role],
        members=len(members),
        expires_at=expires_at(team),
        is_member=any(m.user_id == user.id for m, _ in members),
    )


@router.post("/teams/invite/{code}/join", response_model=TeamOut)
async def join(
    code: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
    now: datetime = Depends(get_now),
):
    team = await _by_code(db, code, lock=True)
    await _apply(db, join_team(db, team, user, now))
    return await _out(db, team, user, now)


@router.get("/teams/{team_id}", response_model=TeamOut)
async def get_team(
    team_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
    now: datetime = Depends(get_now),
):
    return await _out(db, await _member_team(db, team_id, user), user, now)


@router.put("/teams/{team_id}/role", response_model=TeamOut)
async def set_role(
    team_id: uuid.UUID,
    body: RoleClaim,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
    now: datetime = Depends(get_now),
):
    team = await _member_team(db, team_id, user, lock=True)
    await _apply(db, claim_role(db, team, user.id, body.role, now))
    return await _out(db, team, user, now)


@router.post("/teams/{team_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave(
    team_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
    now: datetime = Depends(get_now),
):
    team = await _member_team(db, team_id, user, lock=True)
    await _apply(db, leave_team(db, team, user.id, now))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/teams/{team_id}/members/{member_id}/remove", response_model=TeamOut)
async def remove(
    team_id: uuid.UUID,
    member_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
    now: datetime = Depends(get_now),
):
    team = await _member_team(db, team_id, user, lock=True)
    await _apply(db, remove_member(db, team, user.id, member_id, now))
    return await _out(db, team, user, now)


@router.post("/teams/{team_id}/disband", response_model=TeamOut)
async def disband_team(
    team_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
    now: datetime = Depends(get_now),
):
    team = await _member_team(db, team_id, user, lock=True)
    await _apply(db, disband(db, team, user.id, now))
    return await _out(db, team, user, now)


@router.post("/teams/{team_id}/start", response_model=RunCreatedOut, status_code=status.HTTP_201_CREATED)
async def start(
    team_id: uuid.UUID,
    body: TeamStart,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
    now: datetime = Depends(get_now),
):
    team = await _member_team(db, team_id, user, lock=True)
    try:
        run, info = await start_team(db, team, user.id, now, body.start_at)
        notes = await advance_run(db, run, now)
        await db.commit()
    except EngineError as exc:
        await db.rollback()
        raise _engine_error(exc)
    except IntegrityError:
        # parallel so'rov: qisman UNIQUE (kapitanning bitta ochiq Run'i) ushladi
        await db.rollback()
        raise HTTPException(status_code=409, detail="Bu ssenariyda tugallanmagan Run bor")
    await notify.publish(notes)
    return RunCreatedOut(run=await _detail(db, run, now, user.id), warning=info.warning, day1_ends_at=info.day1_ends_at)
