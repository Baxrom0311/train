"""
Jamoaviy Run (CONTRACT.md §29): lobby, rollar taqsimoti va Run ichidagi jamoa.

- Lobby (`run_teams`, `run_team_members`): kapitan jamoa ochadi, a'zolar
  taklif kodi bilan qo'shiladi va rol band qiladi, kapitan boshlaydi.
- Boshlanganda band qilinmagan rollar kam rolli a'zoga taqsimlanadi
  (`assign_roles`), Run `user_id = kapitan`, `team_id` bilan yaratiladi.
- Run davomida a'zo chiqsa rollari qolganlarga o'tadi (`redistribute`).

Rol taqsimoti — sof funksiyalar; qolganlari chaqiruvchining
tranzaksiyasida ishlaydi (commit — API'da). Jamoa qatori o'zgarishdan
oldin `FOR UPDATE` bilan qulflanadi: ikki kishi bir vaqtda oxirgi joyga
qo'shilsa yoki bitta rolni band qilsa ham holat buzilmaydi.
"""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.credentials.issue import ALPHABET
from app.models.scenario import (
    TEAM_DISBANDED,
    TEAM_FORMING,
    TEAM_STARTED,
    Run,
    RunTeam,
    RunTeamMember,
    ScenarioVersion,
)
from app.models.user import User
from app.notifications.teams import team_joined, team_started
from app.scenario.engine import (
    Conflict,
    Forbidden,
    Invalid,
    Note,
    NotFound,
    StartInfo,
    create_run,
    definition_for,
    open_run_holders,
)
from app.scenario.limits import DAILY_AI_MESSAGES, RUN_AI_TOKEN_BUDGET
from app.scenario.schema import Node, ScenarioDefinition, Team

# §29.2 — yig'ilayotgan jamoa shuncha vaqtdan keyin yonadi
INVITE_TTL = timedelta(days=7)
INVITE_CODE_LENGTH = 8
STATE_EXPIRED = "expired"


def seat_order(captain_id: uuid.UUID) -> tuple:
    """A'zolar tartibi: kapitan, keyin qo'shilish vaqti (bir paytda qo'shilganlar — barqaror)."""
    return (case((RunTeamMember.user_id == captain_id, 0), else_=1), RunTeamMember.joined_at, RunTeamMember.user_id)


# ── Rol taqsimoti (sof) ───────────────────────────────────────────────


def assign_roles(roles: list[str], seats: list[tuple[uuid.UUID, str | None]]) -> dict[uuid.UUID, list[str]]:
    """
    §29.2: `seats` — a'zolar qo'shilish tartibida `(user_id, band qilgan rol)`.
    Band qilingan rol egasida qoladi; bo'sh rollar (ssenariy tartibida) eng
    kam rolli a'zoga, teng bo'lsa — oldin qo'shilganga. A'zolar rollardan
    ko'p bo'lmaydi, shuning uchun har a'zoda kamida bitta rol bo'ladi.
    """
    order = {user_id: i for i, (user_id, _) in enumerate(seats)}
    held = {user_id: [role] if role in roles else [] for user_id, role in seats}
    taken = {r for rs in held.values() for r in rs}
    for role in roles:
        if role not in taken:
            target = min(held, key=lambda u: (len(held[u]), order[u]))
            held[target].append(role)
    # rollar ssenariydagi tartibda — UI va hisobot barqaror bo'lsin
    return {u: sorted(rs, key=roles.index) for u, rs in held.items()}


def redistribute(
    holdings: dict[uuid.UUID, list[str]], leaving: uuid.UUID, roles: list[str],
) -> dict[uuid.UUID, list[str]]:
    """§29.3: chiqqan a'zoning rollari qolganlarga — eng kam rolliga, teng bo'lsa oldingi a'zoga."""
    order = {user_id: i for i, user_id in enumerate(holdings)}
    out = {u: list(rs) for u, rs in holdings.items() if u != leaving}
    if not out:
        raise ValueError("jamoada boshqa a'zo qolmadi")
    for role in holdings.get(leaving, []):
        target = min(out, key=lambda u: (len(out[u]), order[u]))
        out[target].append(role)
    return {u: sorted(rs, key=roles.index) for u, rs in out.items()}


# ── Run ichidagi jamoa ko'rinishi ─────────────────────────────────────


@dataclass(frozen=True)
class MemberView:
    user_id: uuid.UUID
    name: str
    roles: tuple[str, ...]
    joined_at: datetime
    left_at: datetime | None

    @property
    def active(self) -> bool:
        return self.left_at is None


@dataclass(frozen=True)
class TeamView:
    """Jamoaviy Run'ning a'zolari (qo'shilish tartibida, chiqqanlari ham)."""
    team_id: uuid.UUID
    captain_id: uuid.UUID
    spec: Team
    members: tuple[MemberView, ...]

    @property
    def active(self) -> list[MemberView]:
        return [m for m in self.members if m.active]

    @property
    def active_ids(self) -> list[uuid.UUID]:
        return [m.user_id for m in self.active]

    def holder(self, role: str) -> uuid.UUID | None:
        return next((m.user_id for m in self.active if role in m.roles), None)

    def member(self, user_id: uuid.UUID) -> MemberView | None:
        return next((m for m in self.members if m.user_id == user_id), None)

    def name(self, user_id: uuid.UUID | None) -> str | None:
        m = self.member(user_id) if user_id else None
        return m.name if m else None

    def label(self, user_id: uuid.UUID | None) -> str:
        """AI kontekstidagi muallif belgisi: "Ism (rol)"."""
        m = self.member(user_id) if user_id else None
        if m is None:
            return "Jamoa a'zosi"
        titles = ", ".join(self.spec.role(r).title for r in m.roles)
        return f"{m.name} ({titles})" if titles else m.name

    def recipients(self, node: Node | None) -> list[uuid.UUID]:
        """§29.5: rolli hodisa — rol egasiga, umumiy — barcha faol a'zolarga."""
        if node is not None and node.role is not None and (holder := self.holder(node.role)):
            return [holder]
        return self.active_ids


async def team_view(db: AsyncSession, run: Run, defn: ScenarioDefinition | None = None) -> TeamView | None:
    if run.team_id is None:
        return None
    if defn is None:
        defn = definition_for(await db.get(ScenarioVersion, run.scenario_version_id))
    team = await db.get(RunTeam, run.team_id)
    rows = (await db.execute(
        select(RunTeamMember, User.full_name)
        .join(User, User.id == RunTeamMember.user_id)
        .where(RunTeamMember.team_id == run.team_id)
        .order_by(*seat_order(team.captain_id))
    )).all()
    return TeamView(
        team_id=team.id,
        captain_id=team.captain_id,
        spec=defn.team,
        members=tuple(
            MemberView(user_id=m.user_id, name=name, roles=tuple(m.roles or ()), joined_at=m.joined_at,
                       left_at=m.left_at)
            for m, name in rows
        ),
    )


async def run_recipients(db: AsyncSession, run: Run, node: Node | None = None) -> list[uuid.UUID]:
    """Bildirishnoma kimga (§29.5): yakka Run — egasiga."""
    view = await team_view(db, run)
    return [run.user_id] if view is None else view.recipients(node)


async def ai_limits(db: AsyncSession, run: Run) -> tuple[int, int]:
    """
    (kunlik AI xabar limiti, token byudjeti) — §9.4. Jamoaviy Run'da (§29.3)
    kunlik limit faol a'zolar soniga, byudjet barcha a'zolar soniga ko'paytiriladi.
    """
    if run.team_id is None:
        return DAILY_AI_MESSAGES, RUN_AI_TOKEN_BUDGET
    total, active = (await db.execute(
        select(func.count(), func.count().filter(RunTeamMember.left_at.is_(None)))
        .where(RunTeamMember.team_id == run.team_id)
    )).one()
    return DAILY_AI_MESSAGES * max(active, 1), RUN_AI_TOKEN_BUDGET * max(total, 1)


async def leave_run(db: AsyncSession, run: Run, actor_id: uuid.UUID, now: datetime) -> list[Note]:
    """§29.3: a'zo (kapitan emas) Run'dan chiqadi — rollari qolganlarga o'tadi. Run qulflangan bo'lishi kerak."""
    if run.team_id is None:
        raise NotFound("Bu Run jamoaviy emas")
    if actor_id == run.user_id:
        raise Conflict("Kapitan jamoadan chiqmaydi — Run'ni to'xtatishi mumkin")
    members = (await db.execute(
        select(RunTeamMember)
        .where(RunTeamMember.team_id == run.team_id, RunTeamMember.left_at.is_(None))
        .order_by(*seat_order(run.user_id))
    )).scalars().all()
    me = next((m for m in members if m.user_id == actor_id), None)
    if me is None:
        raise NotFound("Run topilmadi")
    defn = definition_for(await db.get(ScenarioVersion, run.scenario_version_id))
    roles = [r.key for r in defn.team.roles]
    holdings = redistribute({m.user_id: list(m.roles or []) for m in members}, actor_id, roles)
    for m in members:
        if m.user_id == actor_id:
            m.left_at = now
            m.roles = []
        else:
            m.roles = holdings[m.user_id]
    await db.flush()
    return [Note(run.id, "team", {"left": str(actor_id)})]


# ── Lobby ─────────────────────────────────────────────────────────────


def expires_at(team: RunTeam) -> datetime:
    return team.created_at + INVITE_TTL


def team_state(team: RunTeam, now: datetime) -> str:
    """`forming | expired | started | disbanded` (§29.2)."""
    if team.status == TEAM_FORMING and expires_at(team) <= now:
        return STATE_EXPIRED
    return team.status


def team_spec(version: ScenarioVersion) -> Team:
    spec = definition_for(version).team
    if spec is None:
        raise Invalid("Bu ssenariy jamoaviy emas")
    return spec


def _new_code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(INVITE_CODE_LENGTH))


def normalize_invite(raw: str) -> str:
    return "".join(raw.split()).replace("-", "").upper()


async def _unused_code(db: AsyncSession) -> str:
    for _ in range(5):
        code = _new_code()
        if not await db.scalar(select(RunTeam.id).where(RunTeam.invite_code == code)):
            return code
    raise RuntimeError("taklif kodi topilmadi")   # 31^8 — amalda bo'lmaydi


async def _ensure_free(db: AsyncSession, user_id: uuid.UUID, version: ScenarioVersion, now: datetime) -> None:
    """Shu ssenariyda boshqa yig'ilayotgan jamoa ham, ochiq Run ham yo'q (§29.2)."""
    busy = await db.scalar(
        select(RunTeam.id)
        .join(RunTeamMember, RunTeamMember.team_id == RunTeam.id)
        .where(
            RunTeamMember.user_id == user_id,
            RunTeam.scenario_id == version.scenario_id,
            RunTeam.status == TEAM_FORMING,
            RunTeam.created_at > now - INVITE_TTL,
        )
        .limit(1)
    )
    if busy is not None:
        raise Conflict("Siz bu ssenariy bo'yicha boshqa jamoadasiz")
    if await open_run_holders(db, [user_id], version.id):
        raise Conflict("Bu ssenariyda tugallanmagan Run'ingiz bor")


async def create_team(db: AsyncSession, user: User, version: ScenarioVersion, now: datetime) -> RunTeam:
    team_spec(version)
    await _ensure_free(db, user.id, version, now)
    team = RunTeam(
        id=uuid.uuid4(),
        scenario_id=version.scenario_id,
        scenario_version_id=version.id,
        captain_id=user.id,
        invite_code=await _unused_code(db),
        status=TEAM_FORMING,
        created_at=now,
    )
    db.add(team)
    await db.flush()
    db.add(RunTeamMember(team_id=team.id, user_id=user.id, roles=[], joined_at=now))
    await db.flush()
    return team


async def _members(db: AsyncSession, team: RunTeam) -> list[RunTeamMember]:
    return list((await db.execute(
        select(RunTeamMember).where(RunTeamMember.team_id == team.id)
        .order_by(*seat_order(team.captain_id))
    )).scalars())


async def lock_team(db: AsyncSession, team_id: uuid.UUID) -> RunTeam:
    team = (await db.execute(select(RunTeam).where(RunTeam.id == team_id).with_for_update())).scalars().first()
    if team is None:
        raise NotFound("Jamoa topilmadi")
    return team


def _require_forming(team: RunTeam, now: datetime) -> None:
    state = team_state(team, now)
    if state == STATE_EXPIRED:
        raise Conflict("Taklif muddati o'tgan — yangi jamoa tuzing")
    if state != TEAM_FORMING:
        raise Conflict("Jamoa allaqachon boshlangan yoki tarqatilgan")


async def join_team(db: AsyncSession, team: RunTeam, user: User, now: datetime) -> None:
    """Jamoa qulflangan bo'lishi kerak."""
    _require_forming(team, now)
    members = await _members(db, team)
    if any(m.user_id == user.id for m in members):
        raise Conflict("Siz allaqachon shu jamoadasiz")
    version = await db.get(ScenarioVersion, team.scenario_version_id)
    if len(members) >= team_spec(version).max_size:
        raise Conflict("Jamoada bo'sh joy qolmagan")
    await _ensure_free(db, user.id, version, now)
    db.add(RunTeamMember(team_id=team.id, user_id=user.id, roles=[], joined_at=now))
    await db.flush()
    await team_joined(db, team, user.full_name, user.id, now)


async def claim_role(db: AsyncSession, team: RunTeam, user_id: uuid.UUID, role: str | None, now: datetime) -> None:
    """Lobbyda rol band qilish yoki bo'shatish (`None`). Jamoa qulflangan bo'lishi kerak."""
    _require_forming(team, now)
    members = await _members(db, team)
    me = next((m for m in members if m.user_id == user_id), None)
    if me is None:
        raise NotFound("Jamoa topilmadi")
    if role is not None:
        spec = team_spec(await db.get(ScenarioVersion, team.scenario_version_id))
        if role not in {r.key for r in spec.roles}:
            raise Invalid("Bunday rol yo'q")
        if any(m.role == role and m.user_id != user_id for m in members):
            raise Conflict("Bu rolni boshqa a'zo band qilgan")
    me.role = role
    await db.flush()


async def leave_team(db: AsyncSession, team: RunTeam, user_id: uuid.UUID, now: datetime) -> None:
    _require_forming(team, now)
    if user_id == team.captain_id:
        raise Conflict("Kapitan jamoadan chiqmaydi — jamoani tarqatishi mumkin")
    await _remove(db, team, user_id)


async def remove_member(db: AsyncSession, team: RunTeam, actor_id: uuid.UUID, user_id: uuid.UUID, now: datetime) -> None:
    if actor_id != team.captain_id:
        raise Forbidden("Faqat kapitan a'zoni chiqaradi")
    _require_forming(team, now)
    if user_id == team.captain_id:
        raise Conflict("Kapitan o'zini chiqarmaydi")
    await _remove(db, team, user_id)


async def _remove(db: AsyncSession, team: RunTeam, user_id: uuid.UUID) -> None:
    member = await db.get(RunTeamMember, (team.id, user_id))
    if member is None:
        raise NotFound("A'zo topilmadi")
    await db.delete(member)
    await db.flush()


async def disband(db: AsyncSession, team: RunTeam, actor_id: uuid.UUID, now: datetime) -> None:
    if actor_id != team.captain_id:
        raise Forbidden("Faqat kapitan jamoani tarqatadi")
    if team.status != TEAM_FORMING:
        raise Conflict("Boshlangan jamoani tarqatib bo'lmaydi")
    team.status = TEAM_DISBANDED
    await db.flush()


async def start_team(
    db: AsyncSession, team: RunTeam, actor_id: uuid.UUID, now: datetime, requested_start: datetime | None,
) -> tuple[Run, StartInfo]:
    """§29.2: rollar taqsimlanadi va jamoaviy Run yaratiladi. Jamoa qulflangan bo'lishi kerak."""
    if actor_id != team.captain_id:
        raise Forbidden("Faqat kapitan boshlaydi")
    _require_forming(team, now)
    version = await db.get(ScenarioVersion, team.scenario_version_id)
    spec = team_spec(version)
    members = await _members(db, team)
    if len(members) < spec.min_size:
        raise Conflict(f"Boshlash uchun kamida {spec.min_size} a'zo kerak")
    users = {u.id: u for u in (await db.execute(
        select(User).where(User.id.in_([m.user_id for m in members]))
    )).scalars()}
    if inactive := [users[m.user_id].full_name for m in members if not users[m.user_id].is_active]:
        raise Conflict(f"Faol bo'lmagan a'zo: {', '.join(inactive)}")
    if busy := await open_run_holders(db, list(users), version.id):
        names = ", ".join(users[u].full_name for u in users if u in busy)
        raise Conflict(f"Bu ssenariyda tugallanmagan Run'i bor: {names}")

    held = assign_roles([r.key for r in spec.roles], [(m.user_id, m.role) for m in members])
    run, info = await create_run(
        db, team.captain_id, version, now, requested_start,
        team_id=team.id, participants=[m.user_id for m in members],
    )
    for m in members:
        m.roles = held[m.user_id]
    team.status = TEAM_STARTED
    team.started_at = now
    await db.flush()
    titles = {r.key: r.title for r in spec.roles}
    await team_started(
        db, team, run, users[team.captain_id].full_name,
        {m.user_id: [titles[r] for r in held[m.user_id]] for m in members}, now,
    )
    return run, info
