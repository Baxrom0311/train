"""`/scenarios`, `/runs`, `/admin/holidays` API (CONTRACT.md §9.9)."""
import uuid
from datetime import datetime
from pathlib import Path

import pytest
import yaml
from sqlalchemy import select

from app.api.runs import get_eval_queue, get_now
from app.main import app
from app.models.rbac import Permission, Role
from app.scenario.clock import TASHKENT
from app.scenario.importer import import_scenario, publish_version
from app.scenario.schema import ScenarioDefinition

FIXTURE = Path(__file__).parent / "fixtures" / "scenarios" / "elon-market-backend-day1.yaml"


class Clock:
    def __init__(self):
        self.now = datetime(2026, 10, 7, 9, 0, tzinfo=TASHKENT)

    def set(self, hhmm: str, day: int = 7):
        h, m = map(int, hhmm.split(":"))
        self.now = datetime(2026, 10, day, h, m, tzinfo=TASHKENT)


class FakeQueue:
    def __init__(self):
        self.jobs = []

    async def enqueue_job(self, name, *args, **kwargs):
        self.jobs.append((name, args, kwargs))


@pytest.fixture
def clock():
    c = Clock()
    app.dependency_overrides[get_now] = lambda: c.now
    yield c
    app.dependency_overrides.pop(get_now, None)


@pytest.fixture
def queue():
    q = FakeQueue()
    app.dependency_overrides[get_eval_queue] = lambda: q
    yield q
    app.dependency_overrides.pop(get_eval_queue, None)


@pytest.fixture
async def scenario(db_session):
    defn = ScenarioDefinition.model_validate(yaml.safe_load(FIXTURE.read_text(encoding="utf-8")))
    version, _ = await import_scenario(db_session, defn)
    await publish_version(db_session, version)
    await db_session.commit()
    return version.scenario_id


async def _login(client, factory, email, role="student"):
    await factory(email, "pass", role)
    r = await client.post("/api/v1/auth/login", data={"username": email, "password": "pass"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_catalog_lists_published_only(client, db_session, test_user_factory, scenario):
    h = await _login(client, test_user_factory, "cat@example.com")
    draft = ScenarioDefinition.model_validate({
        **yaml.safe_load(FIXTURE.read_text(encoding="utf-8")), "slug": "draft-only", "title": "Draft",
    })
    await import_scenario(db_session, draft)
    await db_session.commit()

    r = await client.get("/api/v1/scenarios", headers=h)
    assert r.status_code == 200
    assert [s["slug"] for s in r.json()] == ["elon-market-backend-day1"]

    r = await client.get(f"/api/v1/scenarios/{scenario}", headers=h)
    assert r.status_code == 200
    body = r.text
    assert "dilnoza" in body and "secrets" not in body and "refund" not in body.lower()


async def test_run_flow(client, test_user_factory, scenario, clock, queue):
    h = await _login(client, test_user_factory, "flow@example.com")
    r = await client.post("/api/v1/runs", json={"scenario_id": str(scenario)}, headers=h)
    assert r.status_code == 201, r.text
    body = r.json()
    run_id = body["run"]["id"]
    assert body["warning"] is None and body["run"]["status"] == "active"
    assert [e["node_id"] for e in body["run"]["events"]] == ["welcome", "standup"]   # ssenariy tartibi

    # bitta ochiq Run
    r = await client.post("/api/v1/runs", json={"scenario_id": str(scenario)}, headers=h)
    assert r.status_code == 409

    r = await client.post(f"/api/v1/runs/{run_id}/events/standup/submit", json={"text": "Reja: bug"}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["attempt"] == 1 and r.json()["ai_eval_status"] == "pending"
    assert queue.jobs and queue.jobs[0][0] == "evaluate_run_submission_job"

    # GET ham advance qiladi
    clock.set("09:30")
    r = await client.get(f"/api/v1/runs/{run_id}", headers=h)
    events = {e["node_id"]: e for e in r.json()["events"]}
    bug = events["bug_orders"]
    assert bug["status"] == "delivered" and bug["answer_types"] == ["code", "text"]
    assert "rubric" not in r.text and "reference_answer" not in r.text and "hints" not in r.text

    r = await client.post(f"/api/v1/runs/{run_id}/events/bug_orders/submit", json={"link_url": "https://x.example"}, headers=h)
    assert r.status_code == 422

    r = await client.get("/api/v1/runs/my", headers=h)
    assert [x["id"] for x in r.json()] == [run_id]

    r = await client.post(f"/api/v1/runs/{run_id}/abandon", headers=h)
    assert r.json()["status"] == "abandoned"
    r = await client.post(f"/api/v1/runs/{run_id}/events/bug_orders/submit", json={"text": "x"}, headers=h)
    assert r.status_code == 409


async def test_late_start_warning(client, test_user_factory, scenario, clock, queue):
    h = await _login(client, test_user_factory, "late@example.com")
    clock.set("15:00")
    r = await client.post("/api/v1/runs", json={"scenario_id": str(scenario)}, headers=h)
    body = r.json()
    assert body["warning"] and body["day1_ends_at"].startswith("2026-10-08T10:00")   # 15:00 Toshkent = 10:00 UTC


async def test_runs_are_private(client, test_user_factory, scenario, clock, queue):
    owner = await _login(client, test_user_factory, "own@example.com")
    other = await _login(client, test_user_factory, "oth@example.com")
    run_id = (await client.post("/api/v1/runs", json={"scenario_id": str(scenario)}, headers=owner)).json()["run"]["id"]
    assert (await client.get(f"/api/v1/runs/{run_id}", headers=other)).status_code == 404
    assert (await client.post(f"/api/v1/runs/{run_id}/abandon", headers=other)).status_code == 404
    r = await client.post(f"/api/v1/runs/{run_id}/events/standup/submit", json={"text": "x"}, headers=other)
    assert r.status_code == 404
    assert (await client.get(f"/api/v1/runs/{uuid.uuid4()}", headers=owner)).status_code == 404


async def test_unknown_scenario(client, test_user_factory, clock):
    h = await _login(client, test_user_factory, "unk@example.com")
    r = await client.post("/api/v1/runs", json={"scenario_id": str(uuid.uuid4())}, headers=h)
    assert r.status_code == 404


async def test_admin_holidays(client, db_session, test_user_factory):
    perm = Permission(id=uuid.uuid4(), key="manage_simulations")
    db_session.add(perm)
    admin_role = (await db_session.execute(select(Role).where(Role.name == "admin"))).scalars().first()
    admin_role.permissions.append(perm)
    await db_session.commit()

    student = await _login(client, test_user_factory, "hs@example.com")
    admin = await _login(client, test_user_factory, "ha@example.com", role="admin")
    assert (await client.get("/api/v1/admin/holidays", headers=student)).status_code == 403

    r = await client.put("/api/v1/admin/holidays/2026-10-08", json={"name": "Qo'shimcha dam olish"}, headers=admin)
    assert r.status_code == 200 and r.json()["source"] == "manual"
    r = await client.get("/api/v1/admin/holidays?year=2026", headers=admin)
    assert [h["date"] for h in r.json()] == ["2026-10-08"]
    assert (await client.delete("/api/v1/admin/holidays/2026-10-08", headers=admin)).status_code == 204
    assert (await client.delete("/api/v1/admin/holidays/2026-10-08", headers=admin)).status_code == 404
