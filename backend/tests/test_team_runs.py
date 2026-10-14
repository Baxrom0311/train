"""Jamoaviy Run (CONTRACT.md §29): rollar, lobby, rolli harakatlar, jamoa chati, hisobot va bildirishnomalar."""
import uuid
from datetime import timedelta
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError
from sqlalchemy import select

from app.ai.reports import FinalSummary
from app.models.enums import AIEvalStatus, ChatSender, RunEventStatus, RunStatus
from app.models.notification import Notification
from app.models.scenario import ChatMessage, RunTeam, RunTeamMember
from app.models.simulation import Submission
from app.models.user import User
from app.notifications.run_events import deadline_reminders, from_notes
from app.scenario.engine import Answer, advance, create_run, decide, submit_answer
from app.scenario.importer import import_scenario, publish_version
from app.scenario.reports import write_final_report
from app.scenario.schema import ScenarioDefinition
from app.scenario.team import assign_roles, redistribute
from app.talent.profile import load_profiles
from tests.test_runs_api import FIXTURE, _login, clock, queue  # noqa: F401 — fixture'lar
from tests.test_runs_chat import ai  # noqa: F401
from tests.test_runs_engine import T, _events

TEAM_FILE = Path(__file__).resolve().parents[1] / "content" / "scenarios" / "lazurit-go-express-team-day1.yaml"


def _team_defn() -> ScenarioDefinition:
    return ScenarioDefinition.model_validate(yaml.safe_load(TEAM_FILE.read_text(encoding="utf-8")))


@pytest.fixture
async def team_scenario(db_session):
    version, _ = await import_scenario(db_session, _team_defn())
    await publish_version(db_session, version)
    await db_session.commit()
    return version


async def _named(db, email: str, name: str):
    user = (await db.execute(select(User).where(User.email == email))).scalars().one()
    user.full_name = name
    await db.commit()
    return user


async def _member(client, db, factory, email, name):
    h = await _login(client, factory, email)
    user = await _named(db, email, name)
    return h, user


# ── Rol taqsimoti (sof) ───────────────────────────────────────────────

A, B, C = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
ROLES = ["backend", "analyst", "support"]


def test_assign_roles_keeps_claims_and_fills_fewest():
    assert assign_roles(ROLES, [(A, None), (B, "analyst"), (C, None)]) == {
        A: ["backend"], B: ["analyst"], C: ["support"]}
    # ikki kishi, uchta rol: band qilinmaganlari eng kam rolliga, teng bo'lsa oldin qo'shilganga
    assert assign_roles(ROLES, [(A, "support"), (B, None)]) == {A: ["analyst", "support"], B: ["backend"]}
    assert assign_roles(ROLES, [(A, None), (B, None)]) == {A: ["backend", "support"], B: ["analyst"]}
    # eski versiyadan qolgan noma'lum rol e'tiborsiz
    assert assign_roles(["backend", "analyst"], [(A, "support"), (B, None)]) == {A: ["backend"], B: ["analyst"]}


def test_redistribute_moves_roles_of_leaver():
    holdings = {A: ["backend"], B: ["analyst"], C: ["support"]}
    assert redistribute(holdings, C, ROLES) == {A: ["backend", "support"], B: ["analyst"]}
    assert redistribute({A: ["backend", "support"], B: ["analyst"]}, B, ROLES) == {A: ["backend", "analyst", "support"]}
    with pytest.raises(ValueError):
        redistribute({A: ["backend"]}, A, ROLES)


# ── Sxema (§29.1) ─────────────────────────────────────────────────────


def _with(**changes) -> dict:
    data = yaml.safe_load(TEAM_FILE.read_text(encoding="utf-8"))
    for key, value in changes.items():
        data[key] = value(data) if callable(value) else value
    return data


def _patch_node(node_id, **fields):
    def apply(data):
        return [{**n, **fields} if n["id"] == node_id else n for n in data["nodes"]]
    return apply


@pytest.mark.parametrize(("changes", "message"), [
    ({"team": None}, "role faqat `team` bloki bor ssenariyda"),
    ({"nodes": _patch_node("fix_express", role="designer")}, "noma'lum rol `designer`"),
    ({"nodes": _patch_node("day1_end", role="backend")}, "role faqat task/incident/decision"),
    ({"nodes": lambda d: [{k: v for k, v in n.items() if k != "role" or v != "support"} for n in d["nodes"]]},
     r"berilmagan: \['support'\]"),
    ({"team": {"min_size": 4, "roles": [{"key": "backend", "title": "B"}, {"key": "analyst", "title": "A"},
                                         {"key": "support", "title": "S"}]}}, "min_size=4"),
    ({"team": {"roles": [{"key": "backend", "title": "B"}]}}, "at least 2"),
])
def test_team_schema_errors(changes, message):
    with pytest.raises(ValidationError, match=message):
        ScenarioDefinition.model_validate(_with(**changes))


def test_team_content_is_valid():
    defn = _team_defn()
    assert [r.key for r in defn.team.roles] == ROLES and defn.team.min_size == 2
    roled = {n.id: n.role for n in defn.nodes if n.role}
    assert set(roled.values()) == set(ROLES)
    assert defn.node("standup").role is None and defn.node("launch_decision").role is None


# ── Lobby (§29.2) ─────────────────────────────────────────────────────


async def _three(client, db, factory, team_scenario):
    """Kapitan Ali jamoa ochadi, Bobur (analitik) va Charos (support) qo'shiladi."""
    ha, ali = await _member(client, db, factory, "ali@example.com", "Ali Valiyev")
    hb, bobur = await _member(client, db, factory, "bobur@example.com", "Bobur Karimov")
    hc, charos = await _member(client, db, factory, "charos@example.com", "Charos Aliyeva")
    r = await client.post("/api/v1/teams", json={"scenario_id": str(team_scenario.scenario_id)}, headers=ha)
    assert r.status_code == 201, r.text
    team = r.json()
    for h, role in ((hb, "analyst"), (hc, "support")):
        r = await client.post(f"/api/v1/teams/invite/{team['invite_code']}/join", headers=h)
        assert r.status_code == 200, r.text
        r = await client.put(f"/api/v1/teams/{team['id']}/role", json={"role": role}, headers=h)
        assert r.status_code == 200, r.text
    return team, (ha, ali), (hb, bobur), (hc, charos)


async def test_lobby_flow(client, db_session, test_user_factory, team_scenario, clock):
    ha, ali = await _member(client, db_session, test_user_factory, "ali@example.com", "Ali Valiyev")
    hb, bobur = await _member(client, db_session, test_user_factory, "bobur@example.com", "Bobur Karimov")
    hc, _ = await _member(client, db_session, test_user_factory, "charos@example.com", "Charos Aliyeva")
    sid = str(team_scenario.scenario_id)

    [s] = (await client.get("/api/v1/scenarios", headers=ha)).json()
    assert s["team"]["min_size"] == 2 and s["team"]["max_size"] == 3
    assert [r["key"] for r in s["team"]["roles"]] == ROLES

    r = await client.post("/api/v1/teams", json={"scenario_id": sid}, headers=ha)
    assert r.status_code == 201
    team = r.json()
    assert team["state"] == "forming" and team["is_captain"] and len(team["invite_code"]) == 8
    assert [m["name"] for m in team["members"]] == ["Ali Valiyev"]
    # shu ssenariyda ikkinchi yig'ilayotgan jamoa — yo'q
    assert (await client.post("/api/v1/teams", json={"scenario_id": sid}, headers=ha)).status_code == 409

    # taklif ko'rinishi a'zo bo'lmaganga ham; kod katta-kichik harf va bo'shliqsiz
    code = team["invite_code"]
    r = await client.get(f"/api/v1/teams/invite/{code.lower()[:4]} {code.lower()[4:]}", headers=hb)
    assert r.status_code == 200
    invite = r.json()
    assert invite["captain_name"] == "Ali Valiyev" and invite["members"] == 1 and not invite["is_member"]
    assert "members" not in team or all("email" not in m for m in team["members"])
    # a'zo bo'lmaganga jamoaning o'zi — 404
    assert (await client.get(f"/api/v1/teams/{team['id']}", headers=hb)).status_code == 404

    r = await client.post(f"/api/v1/teams/invite/{code}/join", headers=hb)
    assert r.status_code == 200 and not r.json()["is_captain"]
    assert (await client.post(f"/api/v1/teams/invite/{code}/join", headers=hb)).status_code == 409
    joined = (await db_session.execute(
        select(Notification).where(Notification.user_id == ali.id, Notification.kind == "team_joined")
    )).scalars().one()
    assert joined.params["member"] == "Bobur Karimov" and joined.link == f"/teams/{team['id']}"

    # rol band qilish: boshqa a'zoning roli — 409, noma'lum — 422, bo'shatish — null
    assert (await client.put(f"/api/v1/teams/{team['id']}/role", json={"role": "analyst"}, headers=hb)).status_code == 200
    assert (await client.put(f"/api/v1/teams/{team['id']}/role", json={"role": "analyst"}, headers=ha)).status_code == 409
    assert (await client.put(f"/api/v1/teams/{team['id']}/role", json={"role": "pm"}, headers=ha)).status_code == 422
    r = await client.put(f"/api/v1/teams/{team['id']}/role", json={"role": None}, headers=hb)
    assert [m["role"] for m in r.json()["members"]] == [None, None]

    # faqat kapitan boshlaydi, chiqaradi, tarqatadi; kapitan chiqmaydi
    assert (await client.post(f"/api/v1/teams/{team['id']}/start", json={}, headers=hb)).status_code == 403
    assert (await client.post(f"/api/v1/teams/{team['id']}/members/{ali.id}/remove", headers=hb)).status_code == 403
    assert (await client.post(f"/api/v1/teams/{team['id']}/leave", headers=ha)).status_code == 409
    r = await client.post(f"/api/v1/teams/{team['id']}/members/{bobur.id}/remove", headers=ha)
    assert [m["name"] for m in r.json()["members"]] == ["Ali Valiyev"]
    # yolg'iz boshlab bo'lmaydi (min_size = 2)
    r = await client.post(f"/api/v1/teams/{team['id']}/start", json={}, headers=ha)
    assert r.status_code == 409 and "kamida 2" in r.json()["detail"]

    # to'liq jamoa (3 = rollar soni) — to'rtinchi sig'maydi
    for h in (hb, hc):
        assert (await client.post(f"/api/v1/teams/invite/{code}/join", headers=h)).status_code == 200
    hd = await _login(client, test_user_factory, "dilshod@example.com")
    r = await client.post(f"/api/v1/teams/invite/{code}/join", headers=hd)
    assert r.status_code == 409 and "bo'sh joy" in r.json()["detail"]

    # a'zo o'zi chiqadi; ro'yxatda faqat yig'ilayotgan jamoalar
    assert (await client.post(f"/api/v1/teams/{team['id']}/leave", headers=hc)).status_code == 204
    assert (await client.get("/api/v1/teams/my", headers=hc)).json() == []
    assert [t["id"] for t in (await client.get("/api/v1/teams/my", headers=hb)).json()] == [team["id"]]

    # tarqatish
    r = await client.post(f"/api/v1/teams/{team['id']}/disband", headers=ha)
    assert r.json()["state"] == "disbanded"
    assert (await client.post(f"/api/v1/teams/invite/{code}/join", headers=hc)).status_code == 409
    assert (await client.get("/api/v1/teams/my", headers=hb)).json() == []


async def test_invite_expires_after_seven_days(client, db_session, test_user_factory, team_scenario, clock):
    ha = await _login(client, test_user_factory, "cap@example.com")
    hb = await _login(client, test_user_factory, "late@example.com")
    team = (await client.post("/api/v1/teams", json={"scenario_id": str(team_scenario.scenario_id)}, headers=ha)).json()
    clock.set("09:00", day=14)
    r = await client.post(f"/api/v1/teams/invite/{team['invite_code']}/join", headers=hb)
    assert r.status_code == 409 and "muddati" in r.json()["detail"]
    assert (await client.get(f"/api/v1/teams/{team['id']}", headers=ha)).json()["state"] == "expired"
    assert (await client.get("/api/v1/teams/my", headers=ha)).json() == []
    # yongan jamoa yangi jamoa ochishga to'sqinlik qilmaydi
    assert (await client.post("/api/v1/teams", json={"scenario_id": str(team_scenario.scenario_id)}, headers=ha)).status_code == 201


async def test_team_only_from_team_catalog_scenario(client, db_session, test_user_factory, team_scenario, clock):
    h = await _login(client, test_user_factory, "solo@example.com")
    plain = ScenarioDefinition.model_validate(yaml.safe_load(FIXTURE.read_text(encoding="utf-8")))
    version, _ = await import_scenario(db_session, plain)
    await publish_version(db_session, version)
    await db_session.commit()
    r = await client.post("/api/v1/teams", json={"scenario_id": str(version.scenario_id)}, headers=h)
    assert r.status_code == 422 and "jamoaviy emas" in r.json()["detail"]
    assert (await client.post("/api/v1/teams", json={"scenario_id": str(uuid.uuid4())}, headers=h)).status_code == 404


async def test_open_run_blocks_team_and_vice_versa(client, db_session, test_user_factory, team_scenario, clock):
    ha = await _login(client, test_user_factory, "cap@example.com")
    hb = await _login(client, test_user_factory, "busy@example.com")
    sid = str(team_scenario.scenario_id)
    # Bobur shu ssenariyni yakka o'tyapti — jamoaga qo'shila olmaydi
    assert (await client.post("/api/v1/runs", json={"scenario_id": sid}, headers=hb)).status_code == 201
    team = (await client.post("/api/v1/teams", json={"scenario_id": sid}, headers=ha)).json()
    r = await client.post(f"/api/v1/teams/invite/{team['invite_code']}/join", headers=hb)
    assert r.status_code == 409 and "tugallanmagan" in r.json()["detail"]
    # jamoaviy Run'dagi a'zo yakka Run ochmaydi
    hc = await _login(client, test_user_factory, "member@example.com")
    await client.post(f"/api/v1/teams/invite/{team['invite_code']}/join", headers=hc)
    assert (await client.post(f"/api/v1/teams/{team['id']}/start", json={}, headers=ha)).status_code == 201
    assert (await client.post("/api/v1/runs", json={"scenario_id": sid}, headers=hc)).status_code == 409


async def test_start_reports_members_with_open_runs(client, db_session, test_user_factory, team_scenario, clock):
    """Lobbyda turganida a'zo yakka Run boshlagan bo'lsa — start 409, ismi bilan."""
    ha = await _login(client, test_user_factory, "cap@example.com")
    hb, _ = await _member(client, db_session, test_user_factory, "b@example.com", "Bobur Karimov")
    sid = str(team_scenario.scenario_id)
    team = (await client.post("/api/v1/teams", json={"scenario_id": sid}, headers=ha)).json()
    await client.post(f"/api/v1/teams/invite/{team['invite_code']}/join", headers=hb)
    assert (await client.post("/api/v1/runs", json={"scenario_id": sid}, headers=hb)).status_code == 201
    r = await client.post(f"/api/v1/teams/{team['id']}/start", json={}, headers=ha)
    assert r.status_code == 409 and "Bobur Karimov" in r.json()["detail"]


# ── Jamoaviy Run (§29.3) ──────────────────────────────────────────────


async def test_start_assigns_roles_and_notifies(client, db_session, test_user_factory, team_scenario, clock):
    team, (ha, ali), (hb, bobur), (hc, charos) = await _three(client, db_session, test_user_factory, team_scenario)
    clock.set("08:30")
    r = await client.post(f"/api/v1/teams/{team['id']}/start", json={}, headers=ha)
    assert r.status_code == 201, r.text
    run = r.json()["run"]
    assert run["status"] == "scheduled" and run["is_captain"] and run["team_size"] == 3
    t = run["team"]
    assert t["me"] == str(ali.id) and t["my_roles"] == ["backend"]   # band qilinmagan rol kapitanga
    assert {r["key"]: r["holder_id"] for r in t["roles"]} == {
        "backend": str(ali.id), "analyst": str(bobur.id), "support": str(charos.id)}
    assert (await client.get(f"/api/v1/teams/{team['id']}", headers=hb)).json()["run_id"] == run["id"]
    assert (await client.post(f"/api/v1/teams/invite/{team['invite_code']}/join", headers=hb)).status_code == 409

    started = (await db_session.execute(
        select(Notification).where(Notification.kind == "team_started")
    )).scalars().all()
    assert sorted(n.user_id for n in started) == sorted([bobur.id, charos.id])
    assert {tuple(n.params["roles"]) for n in started} == {("Data analitik",), ("Mijozlar bilan ishlash",)}
    assert all(n.params["captain"] == "Ali Valiyev" and n.link == f"/runs/{run['id']}" for n in started)

    # a'zoning "Run'larim" ro'yxati
    [mine] = (await client.get("/api/v1/runs/my", headers=hb)).json()
    assert mine["id"] == run["id"] and mine["team_size"] == 3 and not mine["is_captain"] and not mine["left"]

    clock.set("09:31")
    r = await client.get(f"/api/v1/runs/{run['id']}", headers=hc)
    assert r.status_code == 200
    events = {e["node_id"]: e for e in r.json()["events"]}
    assert events["fix_express"]["role"] == "backend" and events["standup"]["role"] is None
    assert r.json()["team"]["my_roles"] == ["support"]
    # begona foydalanuvchiga 404
    hx = await _login(client, test_user_factory, "stranger@example.com")
    assert (await client.get(f"/api/v1/runs/{run['id']}", headers=hx)).status_code == 404


async def _started(client, db, factory, team_scenario, clock):
    team, a, b, c = await _three(client, db, factory, team_scenario)
    clock.set("09:00")
    run = (await client.post(f"/api/v1/teams/{team['id']}/start", json={}, headers=a[0])).json()["run"]
    return run["id"], a, b, c


async def test_role_gated_actions(client, db_session, test_user_factory, team_scenario, clock, queue):
    run_id, (ha, ali), (hb, bobur), (hc, charos) = await _started(
        client, db_session, test_user_factory, team_scenario, clock)

    # umumiy standup — istalgan a'zo
    clock.set("09:10")
    r = await client.post(f"/api/v1/runs/{run_id}/events/standup/submit", json={"text": "Reja: ..."}, headers=hc)
    assert r.status_code == 200
    standup = next(e for e in r.json()["run"]["events"] if e["node_id"] == "standup")
    assert standup["submitted_by"] == {"user_id": str(charos.id), "name": "Charos Aliyeva"}

    clock.set("09:40")
    # backend task'ini analitik topshirmaydi, hint ham ololmaydi
    r = await client.post(f"/api/v1/runs/{run_id}/events/fix_express/submit", json={"text": "x"}, headers=hb)
    assert r.status_code == 403 and "Backend dasturchi" in r.json()["detail"]
    assert (await client.post(f"/api/v1/runs/{run_id}/events/fix_express/hint", headers=hb)).status_code == 403
    r = await client.post(f"/api/v1/runs/{run_id}/events/fix_express/submit",
                          json={"code": "def delivery_fee(): ...", "text": "Tuzatdim"}, headers=ha)
    assert r.status_code == 200
    assert (await client.post(f"/api/v1/runs/{run_id}/events/pilot_metrics/submit",
                              json={"text": "80.8%"}, headers=hb)).status_code == 200

    subs = {s.content.split("\n")[0][:8]: s.user_id for s in (await db_session.execute(
        select(Submission).where(Submission.run_id == uuid.UUID(run_id))
    )).scalars()}
    assert subs["Reja: .."] == charos.id and subs["Tuzatdim"] == ali.id and subs["80.8%"] == bobur.id

    # umumiy qaror — birinchi a'zo qabul qiladi
    clock.set("11:31")
    r = await client.post(f"/api/v1/runs/{run_id}/events/launch_decision/decide", json={"option": "pilot_only"},
                          headers=hb)
    assert r.status_code == 200
    r = await client.post(f"/api/v1/runs/{run_id}/events/launch_decision/decide", json={"option": "city_wide"},
                          headers=ha)
    assert r.status_code == 409

    # support'ning reliz xabari backend topshirgach (09:40 + 30 ish daqiqasi) keladi va faqat support'ga
    clock.set("11:32")
    run = (await client.get(f"/api/v1/runs/{run_id}", headers=hc)).json()
    assert any(e["node_id"] == "release_note" for e in run["events"])
    assert (await client.post(f"/api/v1/runs/{run_id}/events/release_note/submit", json={"text": "x"},
                              headers=ha)).status_code == 403


async def test_member_file_and_chat_visible_to_team(client, db_session, test_user_factory, team_scenario, clock,
                                                    queue, ai, tmp_path, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    run_id, (ha, ali), (hb, bobur), _ = await _started(client, db_session, test_user_factory, team_scenario, clock)
    clock.set("09:40")
    pdf = b"%PDF-1.4 " + b"A" * 100
    r = await client.post("/api/v1/files", data={"run_id": run_id},
                          files={"file": ("hisob.pdf", pdf, "application/pdf")}, headers=hb)
    assert r.status_code == 201, r.text
    file_id = r.json()["id"]
    # jamoadoshi ko'radi, begona — yo'q
    assert (await client.get(f"/api/v1/files/{file_id}", headers=ha)).status_code == 200
    hx = await _login(client, test_user_factory, "x@example.com")
    assert (await client.get(f"/api/v1/files/{file_id}", headers=hx)).status_code == 404
    # boshqa a'zoning faylini o'z xabariga qo'sha olmaydi
    r = await client.post(f"/api/v1/runs/{run_id}/chat/aziza", json={"text": "x", "file_id": file_id}, headers=ha)
    assert r.status_code == 422

    # personaj chati umumiy: muallif nomi bilan; AI kim yozganini biladi
    r = await client.post(f"/api/v1/runs/{run_id}/chat/aziza",
                          json={"text": "Pilot jadvali to'liqmi?", "file_id": file_id}, headers=hb)
    assert r.status_code == 200, r.text
    assert r.json()["message"]["author_name"] == "Bobur Karimov"
    assert ai["calls"][-1][2].startswith("Bobur Karimov (Data analitik): Pilot jadvali")
    clock.set("09:41")
    r = await client.post(f"/api/v1/runs/{run_id}/chat/aziza", json={"text": "Men ham qo'shilaman"}, headers=ha)
    _, history, prompt = ai["calls"][-1]
    [earlier] = [t for t in history if t.sender == "student"]
    assert earlier.body.startswith("Bobur Karimov (Data analitik)") and prompt.startswith("Ali Valiyev (Backend")
    messages = (await client.get(f"/api/v1/runs/{run_id}/chat/aziza", headers=ha)).json()
    student = [m for m in messages if m["sender"] == "student"]
    assert [m["author_name"] for m in student] == ["Bobur Karimov", "Ali Valiyev"]


async def test_team_chat(client, db_session, test_user_factory, team_scenario, clock, queue):
    run_id, (ha, ali), (hb, _), _ = await _started(client, db_session, test_user_factory, team_scenario, clock)
    clock.set("09:05")
    r = await client.post(f"/api/v1/runs/{run_id}/team-chat", json={"text": "Standupni men yozaman"}, headers=ha)
    assert r.status_code == 201
    assert r.json()["author_name"] == "Ali Valiyev" and r.json()["persona_key"] == "_team"
    assert (await client.post(f"/api/v1/runs/{run_id}/team-chat", json={"text": "   "}, headers=hb)).status_code == 422
    msgs = (await client.get(f"/api/v1/runs/{run_id}/team-chat", headers=hb)).json()
    assert [(m["author_name"], m["body"]) for m in msgs] == [("Ali Valiyev", "Standupni men yozaman")]
    # jamoa chati personaj emas
    assert (await client.get(f"/api/v1/runs/{run_id}/chat/_team", headers=hb)).status_code == 404
    hx = await _login(client, test_user_factory, "x@example.com")
    assert (await client.get(f"/api/v1/runs/{run_id}/team-chat", headers=hx)).status_code == 404

    # yakka Run'da jamoa chati yo'q
    solo = await client.post("/api/v1/runs", json={"scenario_id": str(team_scenario.scenario_id)}, headers=hx)
    assert (await client.get(f"/api/v1/runs/{solo.json()['run']['id']}/team-chat", headers=hx)).status_code == 404


async def test_leave_and_abandon(client, db_session, test_user_factory, team_scenario, clock, queue):
    run_id, (ha, ali), (hb, bobur), (hc, charos) = await _started(
        client, db_session, test_user_factory, team_scenario, clock)
    clock.set("09:40")
    # kapitan chiqmaydi, a'zo Run'ni to'xtatmaydi
    assert (await client.post(f"/api/v1/runs/{run_id}/leave", headers=ha)).status_code == 409
    r = await client.post(f"/api/v1/runs/{run_id}/abandon", headers=hb)
    assert r.status_code == 403 and "kapitan" in r.json()["detail"]

    r = await client.post(f"/api/v1/runs/{run_id}/leave", headers=hc)
    assert r.status_code == 200 and r.json()["left"]
    run = (await client.get(f"/api/v1/runs/{run_id}", headers=ha)).json()
    assert run["team_size"] == 2
    # support kam rolli a'zoga (teng — oldin qo'shilgan kapitanga)
    assert {r["key"]: r["holder_id"] for r in run["team"]["roles"]}["support"] == str(ali.id)
    assert [m["name"] for m in run["team"]["members"]] == ["Ali Valiyev", "Bobur Karimov"]
    # chiqqan a'zo — ish stoliga 404, hisobot va ro'yxat ochiq
    assert (await client.get(f"/api/v1/runs/{run_id}", headers=hc)).status_code == 404
    assert (await client.get(f"/api/v1/runs/{run_id}/report", headers=hc)).status_code == 200
    [mine] = (await client.get("/api/v1/runs/my", headers=hc)).json()
    assert mine["left"]
    # endi kapitan support task'ini topshira oladi
    assert (await client.post(f"/api/v1/runs/{run_id}/events/complaints_triage/submit", json={"text": "x"},
                              headers=ha)).status_code == 200

    r = await client.post(f"/api/v1/runs/{run_id}/abandon", headers=ha)
    assert r.status_code == 200 and r.json()["status"] == "abandoned"


# ── Bildirishnomalar (§29.5) ──────────────────────────────────────────


async def _engine_team(db, factory, version, names=("Ali", "Bobur", "Charos")):
    """API'siz: jamoa va Run to'g'ridan-to'g'ri (09:00 da)."""
    users = []
    for i, name in enumerate(names):
        u = await factory(f"m{i}-{uuid.uuid4().hex[:6]}@example.com", "pass")
        u.full_name = name
        users.append(u)
    team = RunTeam(id=uuid.uuid4(), scenario_id=version.scenario_id, scenario_version_id=version.id,
                   captain_id=users[0].id, invite_code=uuid.uuid4().hex[:8].upper(), status="started",
                   created_at=T("08:00"), started_at=T("08:00"))
    db.add(team)
    await db.flush()
    holdings = assign_roles(ROLES, [(u.id, None) for u in users])
    for i, u in enumerate(users):
        db.add(RunTeamMember(team_id=team.id, user_id=u.id, roles=holdings[u.id], joined_at=T("08:00") + timedelta(seconds=i)))
    run, _ = await create_run(db, users[0].id, version, T("09:00"), T("09:00"), team_id=team.id,
                              participants=[u.id for u in users])
    await db.commit()
    return run, users


async def test_task_notifications_go_to_role_holder(db_session, test_user_factory, team_scenario):
    run, (ali, bobur, charos) = await _engine_team(db_session, test_user_factory, team_scenario)
    notes = await advance(db_session, T("09:31"))
    await from_notes(db_session, notes, T("09:31"))
    await db_session.commit()
    rows = (await db_session.execute(
        select(Notification.user_id, Notification.params).where(Notification.kind == "task_delivered")
    )).all()
    by_node = {}
    for user_id, params in rows:
        by_node.setdefault(params["node_id"], set()).add(user_id)
    assert by_node["standup"] == {ali.id, bobur.id, charos.id}          # umumiy
    assert by_node["fix_express"] == {ali.id}
    assert by_node["pilot_metrics"] == {bobur.id}
    assert by_node["complaints_triage"] == {charos.id}

    # dedlayn eslatmasi ham rol egasiga: 11:45 da faqat fix_express (dedlayn 12:01) yaqin
    assert await deadline_reminders(db_session, T("11:45")) == 1
    await db_session.commit()
    soon = (await db_session.execute(
        select(Notification.user_id, Notification.params["node_id"].astext).where(Notification.kind == "deadline_soon")
    )).all()
    assert soon == [(ali.id, "fix_express")]
    # qayta chaqiruv takrorlamaydi (eslatma kapitanga emas, rol egasiga yozilgan bo'lsa ham)
    assert await deadline_reminders(db_session, T("11:46")) == 0


# ── Hisobot (§29.4) ───────────────────────────────────────────────────


async def _grade(db, sub, score):
    sub.ai_eval_status = AIEvalStatus.COMPLETED
    sub.ai_score = score
    sub.evaluated_at = sub.submitted_at
    await db.commit()


async def test_full_team_day_and_report(db_session, test_user_factory, team_scenario):
    run, (ali, bobur, charos) = await _engine_team(db_session, test_user_factory, team_scenario)

    async def answer(node, at, user, score, **kw):
        await advance(db_session, at)
        sub, _ = await submit_answer(db_session, run, node, Answer(text=kw.get("text", "javob")), at, actor_id=user.id)
        await db_session.commit()
        await _grade(db_session, sub, score)

    await answer("standup", T("09:10"), charos, 80)
    await advance(db_session, T("09:31"))          # rolli task'lar 09:31 da yetkazildi
    await answer("fix_express", T("10:30"), ali, 90)
    await answer("pilot_metrics", T("11:00"), bobur, 70)
    # support shikoyatlarni o'tkazib yuboradi (09:30 + 90 daq = 11:00 dedlayn)
    await advance(db_session, T("11:31"))
    await decide(db_session, run, "launch_decision", "pilot_only", T("11:35"), actor_id=bobur.id)
    await db_session.commit()
    await answer("release_note", T("11:40"), charos, 60)          # 10:30 + 30 daq dan keyin
    await answer("incident_mitigate", T("15:40"), ali, 85)
    await answer("incident_impact", T("15:45"), bobur, 95)
    await answer("incident_comms", T("15:50"), charos, 75)
    await answer("day1_end", T("17:40"), ali, 80)
    await db_session.refresh(run)
    events = await _events(db_session, run)
    assert events["complaints_triage"].status == RunEventStatus.MISSED
    assert events["lead_on_city_wide"].status == RunEventStatus.SKIPPED
    assert run.status == RunStatus.COMPLETED

    async def final(tasks, competencies, messages, completed):
        return FinalSummary(summary="Jamoa yaxshi ishladi", strengths=["a"], improvements=["b"], initiative_score=60)

    assert await write_final_report(db_session, run.id, T("18:00"), summarize=final)
    await db_session.refresh(run)
    report = run.final_report
    assert report["certificate"] is False and not report["incomplete"]
    tasks = {t["node_id"]: t for t in report["tasks"]}
    assert tasks["fix_express"]["role"] == "backend" and tasks["fix_express"]["by"] == str(ali.id)
    assert tasks["launch_decision"]["by"] == str(bobur.id) and tasks["launch_decision"]["role"] is None
    # topshirilmagan rolli task — rol egasiga
    assert tasks["complaints_triage"]["by"] == str(charos.id) and tasks["complaints_triage"]["score"] == 0

    assert [r["key"] for r in report["team"]["roles"]] == ROLES
    members = {m["name"]: m for m in report["team"]["members"]}
    assert members["Ali"]["roles"] == ["backend"] and members["Ali"]["is_captain"]
    assert members["Ali"]["assigned"] == 3 and members["Ali"]["submitted"] == 3        # fix, mitigate, day_end
    assert members["Bobur"]["overall_score"] == pytest.approx((70 * 2 + 100 * 1 + 95 * 1.5) / 4.5, abs=0.1)
    assert members["Charos"]["assigned"] == 4 and members["Charos"]["submitted"] == 3
    assert members["Charos"]["on_time_rate"] == 75.0
    assert sum(m["share"] for m in members.values()) == pytest.approx(100, abs=0.2)
    assert "technical" in members["Ali"]["competency_scores"]

    # sertifikat yo'q, profilga kirmaydi; hisobot — barcha faol a'zolarga
    assert await load_profiles(db_session, [ali.id, bobur.id, charos.id]) == {}
    ready = (await db_session.execute(
        select(Notification.user_id).where(Notification.kind == "report_ready")
    )).scalars().all()
    assert sorted(ready) == sorted([ali.id, bobur.id, charos.id])


async def test_mentor_nudge_ignores_team_chat(db_session, test_user_factory, team_scenario):
    """Mentor eslatmasi: jamoa chatida yozish personajga yozish hisoblanmaydi (§29.3)."""
    run, (ali, *_rest) = await _engine_team(db_session, test_user_factory, team_scenario)
    await advance(db_session, T("09:31"))
    db_session.add(ChatMessage(run_id=run.id, persona_key="_team", sender=ChatSender.STUDENT, body="kim nima qiladi?",
                               created_at=T("09:35"), author_id=ali.id))
    await db_session.commit()
    await advance(db_session, T("11:31"))          # fix_express: 150 daq oyna → 30 daq oldin eslatma
    await db_session.commit()
    nudges = (await db_session.execute(
        select(ChatMessage.node_id).where(ChatMessage.run_id == run.id, ChatMessage.purpose == "nudge")
    )).scalars().all()
    assert "fix_express" in nudges


async def test_solo_run_of_team_scenario_ignores_roles(db_session, test_user_factory, team_scenario):
    user = await test_user_factory("solo@example.com", "pass")
    run, _ = await create_run(db_session, user.id, team_scenario, T("09:00"), T("09:00"))
    await db_session.commit()
    await advance(db_session, T("09:31"))
    for node in ("fix_express", "pilot_metrics", "complaints_triage"):
        sub, _ = await submit_answer(db_session, run, node, Answer(text="javob"), T("09:40"))
        assert sub.user_id == user.id
    await db_session.commit()

