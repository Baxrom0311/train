"""Ssenariy muharriri API (CONTRACT.md §16): qoralama, tekshiruv, YAML, nashr."""
import copy
import uuid

import pytest
import yaml
from sqlalchemy import func, select

from app.models.rbac import Permission, Role
from app.models.scenario import DocumentChunk, Scenario, ScenarioDocument, ScenarioVersion
from app.scenario.engine import definition_for
from tests.test_runs_api import FIXTURE, _login

BASE = "/api/v1/admin/scenarios"


@pytest.fixture
def data() -> dict:
    return yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture
async def admin(client, db_session, test_user_factory):
    perm = Permission(id=uuid.uuid4(), key="manage_simulations")
    role = (await db_session.execute(select(Role).where(Role.name == "admin"))).scalars().one()
    role.permissions.append(perm)
    await db_session.commit()
    return await _login(client, test_user_factory, "admin@test.uz", "admin")


async def test_permissions(client, test_user_factory, admin, data):
    h = await _login(client, test_user_factory, "st@test.uz")
    assert (await client.get(BASE, headers=h)).status_code == 403
    assert (await client.post(f"{BASE}/validate", json={"definition": data}, headers=h)).status_code == 403
    assert (await client.get(BASE)).status_code == 401


async def test_validate_reports_paths_and_summary(client, admin, data):
    r = (await client.post(f"{BASE}/validate", json={"definition": data}, headers=admin)).json()
    assert r["ok"] and r["errors"] == []
    assert r["summary"] == {"days": 1, "nodes": 6, "graded": 3, "personas": 2, "documents": len(data["documents"]),
                            "mentor": True}

    bad = copy.deepcopy(data)
    bad["nodes"][2]["due_in_minutes"] = -5          # maydon xatosi — yo'li bilan
    r = (await client.post(f"{BASE}/validate", json={"definition": bad}, headers=admin)).json()
    assert not r["ok"] and r["summary"] is None
    assert any(e["path"][:3] == ["nodes", 2, "due_in_minutes"] for e in r["errors"])

    bad = copy.deepcopy(data)
    bad["nodes"][2]["from"] = "nobody"              # ta'rif darajasidagi xato — node id bilan
    r = (await client.post(f"{BASE}/validate", json={"definition": bad}, headers=admin)).json()
    [err] = r["errors"]
    assert err["path"] == [] and err["message"].startswith("bug_orders:")


async def test_create_edit_publish_flow(client, db_session, admin, data):
    r = await client.post(BASE, json={"definition": data}, headers=admin)
    assert r.status_code == 201
    v1 = r.json()
    sid = v1["scenario_id"]
    assert (v1["version"], v1["status"]) == (1, "draft")
    assert (await client.post(BASE, json={"definition": data}, headers=admin)).status_code == 409

    # qoralama joyida yangilanadi: versiya raqami o'zgarmaydi, hujjatlar qayta yoziladi
    edited = copy.deepcopy(data)
    edited["title"] = "Yangi sarlavha"
    edited["documents"][0]["content"] = "Yangilangan hujjat matni.\n\nIkkinchi abzas."
    r = (await client.put(f"{BASE}/{sid}/draft", json={"definition": edited}, headers=admin)).json()
    assert (r["version"], r["status"], r["definition"]["title"]) == (1, "draft", "Yangi sarlavha")
    versions = (await db_session.execute(select(ScenarioVersion).where(ScenarioVersion.scenario_id == sid))).scalars().all()
    assert len(versions) == 1
    doc = (await db_session.execute(select(ScenarioDocument).where(
        ScenarioDocument.scenario_version_id == versions[0].id, ScenarioDocument.key == data["documents"][0]["key"],
    ))).scalars().one()
    assert doc.content.startswith("Yangilangan")
    chunks = await db_session.scalar(select(func.count()).select_from(DocumentChunk).where(DocumentChunk.document_id == doc.id))
    assert chunks >= 1
    # qoralama katalog sarlavhasini o'zgartirmaydi — nashrda yangilanadi
    scenario = await db_session.get(Scenario, versions[0].scenario_id)
    await db_session.refresh(scenario)
    assert scenario.title == data["title"]

    r = (await client.post(f"{BASE}/{sid}/versions/1/publish", headers=admin)).json()
    assert r["status"] == "published" and r["published_at"]
    await db_session.refresh(scenario)
    assert scenario.title == "Yangi sarlavha"
    catalog = (await client.get("/api/v1/scenarios", headers=admin)).json()
    assert [s["title"] for s in catalog] == ["Yangi sarlavha"]

    # nashr qilingan versiya o'zgarmaydi: tahrir — yangi qoralama (v2)
    edited["title"] = "Uchinchi"
    r = (await client.put(f"{BASE}/{sid}/draft", json={"definition": edited}, headers=admin)).json()
    assert (r["version"], r["status"]) == (2, "draft")
    v1_def = (await client.get(f"{BASE}/{sid}/versions/1", headers=admin)).json()["definition"]
    assert v1_def["title"] == "Yangi sarlavha"
    await client.post(f"{BASE}/{sid}/versions/2/publish", headers=admin)
    assert (await client.post(f"{BASE}/{sid}/versions/1/publish", headers=admin)).status_code == 409

    listing = (await client.get(BASE, headers=admin)).json()
    [item] = listing
    assert [(v["version"], v["status"]) for v in item["versions"]] == [(2, "published"), (1, "archived")]
    assert item["runs"] == 0 and item["is_active"]


async def test_draft_rejects_invalid_and_slug_change(client, admin, data):
    sid = (await client.post(BASE, json={"definition": data}, headers=admin)).json()["scenario_id"]
    other = {**data, "slug": "boshqa-slug"}
    r = await client.put(f"{BASE}/{sid}/draft", json={"definition": other}, headers=admin)
    assert r.status_code == 422 and r.json()["detail"]["errors"][0]["path"] == ["slug"]
    bad = {**data, "duration_days": 0}
    r = await client.put(f"{BASE}/{sid}/draft", json={"definition": bad}, headers=admin)
    assert r.status_code == 422 and r.json()["detail"]["errors"][0]["path"] == ["duration_days"]
    assert (await client.put(f"{BASE}/00000000-0000-0000-0000-000000000000/draft", json={"definition": data},
                             headers=admin)).status_code == 404


async def test_draft_edit_refreshes_cached_definition(client, db_session, admin, data):
    v = (await client.post(BASE, json={"definition": data}, headers=admin)).json()
    version = await db_session.get(ScenarioVersion, (await db_session.execute(
        select(ScenarioVersion.id).where(ScenarioVersion.scenario_id == v["scenario_id"]))).scalar_one())
    assert definition_for(version).title == data["title"]       # keshga tushdi
    await client.put(f"{BASE}/{v['scenario_id']}/draft", json={"definition": {**data, "title": "Boshqa"}}, headers=admin)
    await db_session.refresh(version)
    assert definition_for(version).title == "Boshqa"


async def test_yaml_roundtrip(client, admin, data):
    data["nodes"][0]["brief"] = "Xush kelibsiz!\n\nBirinchi ish — standup."
    v = (await client.post(BASE, json={"definition": data}, headers=admin)).json()
    r = await client.get(f"{BASE}/{v['scenario_id']}/versions/1/yaml", headers=admin)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/yaml")
    assert f'filename="{data["slug"]}.yaml"' in r.headers["content-disposition"]
    text = r.text
    assert "busy_reply" not in text           # default'lar yozilmaydi
    assert "brief: |" in text                  # ko'p qatorli matn — blok

    parsed = (await client.post(f"{BASE}/yaml", json={"text": text}, headers=admin)).json()
    assert parsed["errors"] == [] and parsed["definition"] == v["definition"]

    shown = (await client.post(f"{BASE}/to-yaml", json={"definition": v["definition"]}, headers=admin)).json()
    assert shown["text"] == text               # saqlanmagan holat ham xuddi eksport kabi
    raw = (await client.post(f"{BASE}/to-yaml", json={"definition": {"slug": "x", "nodes": []}}, headers=admin)).json()
    assert yaml.safe_load(raw["text"]) == {"slug": "x", "nodes": []}

    broken = (await client.post(f"{BASE}/yaml", json={"text": "slug: [unclosed"}, headers=admin)).json()
    assert broken["definition"] is None and "YAML o'qilmadi" in broken["errors"][0]["message"]
    invalid = (await client.post(f"{BASE}/yaml", json={"text": "slug: x\n"}, headers=admin)).json()
    assert invalid["definition"] == {"slug": "x"} and invalid["errors"]
    scalar = (await client.post(f"{BASE}/yaml", json={"text": "- a\n- b\n"}, headers=admin)).json()
    assert scalar["definition"] is None


async def test_toggle_active_hides_from_catalog(client, admin, data):
    v = (await client.post(BASE, json={"definition": data}, headers=admin)).json()
    await client.post(f"{BASE}/{v['scenario_id']}/versions/1/publish", headers=admin)
    r = await client.patch(f"{BASE}/{v['scenario_id']}", json={"is_active": False}, headers=admin)
    assert r.status_code == 200 and r.json()["is_active"] is False
    assert (await client.get("/api/v1/scenarios", headers=admin)).json() == []
    assert (await client.get("/api/v1/showcase")).json()["scenarios"] == []
