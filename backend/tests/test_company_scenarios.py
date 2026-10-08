"""
Kompaniya ssenariylari va sinov topshirig'i (CONTRACT.md §26).

Asosiy qoidalar: kompaniya ssenariysi faqat egasiga ko'rinadi (katalog, landing,
admin va boshqa kompaniyada yo'q), Run faqat sinov orqali boshlanadi, natija
profil va sertifikatga kirmaydi — faqat shu kompaniyaga.
"""
import copy
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import yaml
from sqlalchemy import func, select

from app.ai.reports import FinalSummary
from app.api import company_scenarios as company_api
from app.api import vacancies as vacancies_api
from app.models.credential import Certificate
from app.models.enums import RunStatus
from app.models.notification import Notification
from app.models.scenario import Run, Scenario
from app.notifications.emails import render
from app.scenario.reports import write_final_report
from app.talent.profile import build_profiles
from tests.test_runs_api import FIXTURE
from tests.test_vacancies import _no_expire, _open_vacancy, world  # noqa: F401 — fixture'lar

T0 = datetime(2026, 10, 12, 6, 0, tzinfo=timezone.utc)       # dushanba, 11:00 Toshkent
URL = "/api/v1/company/scenarios"


@pytest.fixture
def data() -> dict:
    d = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    d["slug"] = "alpha-backend-sinov"
    d["company_name"] = "Begona nom"
    return d


@pytest.fixture
def clock(monkeypatch):
    now = [T0]
    monkeypatch.setattr(vacancies_api, "_now", lambda: now[0])
    return now


async def _publish(client, headers, data) -> str:
    r = await client.post(URL, headers=headers, json={"definition": data})
    assert r.status_code == 201, r.text
    sid = r.json()["scenario_id"]
    assert (await client.post(f"{URL}/{sid}/versions/1/publish", headers=headers)).status_code == 200
    return sid


async def _final(tasks, competencies, messages, completed):
    return FinalSummary(summary="Talaba buyurtmalar xatosini tez topdi.", strengths=["Tahlil"],
                        improvements=["Testlar"], initiative_score=70)


async def test_company_scenario_is_private(client, db_session, world, data, monkeypatch):
    w = world
    r = await client.post(URL, headers=w.alpha_h, json={"definition": data})
    assert r.status_code == 201, r.text
    created = r.json()
    sid = created["scenario_id"]
    assert created["definition"]["company_name"] == "Alpha" and created["status"] == "draft"
    scenario = await db_session.get(Scenario, uuid.UUID(sid))
    assert scenario.owner_company_id == w.alpha.id

    # boshqa kompaniya, talaba va admin muharriri ko'rmaydi
    assert (await client.get(f"{URL}/{sid}/versions/1", headers=w.beta_h)).status_code == 404
    assert (await client.get(URL, headers=w.beta_h)).json() == []
    assert (await client.get(URL, headers=w.shy_h)).status_code == 403
    assert [s["id"] for s in (await client.get(URL, headers=w.alpha_h)).json()] == [sid]

    # slug umumiy fazoda noyob, slug o'zgarmaydi, kompaniya cheklovlari
    assert (await client.post(URL, headers=w.alpha_h, json={"definition": data})).status_code == 409
    other = {**copy.deepcopy(data), "slug": "boshqa-slug"}
    assert (await client.put(f"{URL}/{sid}/draft", headers=w.alpha_h, json={"definition": other})).status_code == 422
    monkeypatch.setattr(company_api, "MAX_DAYS", 0)
    v = (await client.post(f"{URL}/validate", headers=w.alpha_h, json={"definition": data})).json()
    assert not v["ok"] and v["errors"][0]["path"] == ["duration_days"]
    assert (await client.put(f"{URL}/{sid}/draft", headers=w.alpha_h, json={"definition": data})).status_code == 422
    assert (await client.post(f"{URL}/{sid}/versions/1/publish", headers=w.alpha_h)).status_code == 422
    monkeypatch.setattr(company_api, "MAX_DAYS", 5)
    monkeypatch.setattr(company_api, "MAX_SCENARIOS", 1)
    assert (await client.post(URL, headers=w.alpha_h, json={"definition": other})).status_code == 409

    assert (await client.post(f"{URL}/{sid}/versions/1/publish", headers=w.alpha_h)).json()["status"] == "published"
    # nashr qilingan bo'lsa ham katalog, landing va to'g'ridan-to'g'ri Run'da yo'q
    assert sid not in {s["id"] for s in (await client.get("/api/v1/scenarios", headers=w.shy_h)).json()}
    assert data["slug"] not in {s["slug"] for s in (await client.get("/api/v1/showcase")).json()["scenarios"]}
    assert (await client.post("/api/v1/runs", headers=w.shy_h, json={"scenario_id": sid})).status_code == 404


async def test_admin_editor_skips_company_scenarios(client, db_session, world, data):
    from app.models.rbac import Permission, Role
    w = world
    sid = await _publish(client, w.alpha_h, data)
    # admin: muharrir ruxsati bilan, lekin kompaniya ssenariysi "yo'q"
    perm = Permission(id=uuid.uuid4(), key="manage_simulations")
    role = (await db_session.execute(select(Role).where(Role.name == "company_hr"))).scalar_one()
    db_session.add(perm)
    role.permissions.append(perm)
    await db_session.commit()
    assert sid not in {s["id"] for s in (await client.get("/api/v1/admin/scenarios", headers=w.alpha_h)).json()}
    assert (await client.get(f"/api/v1/admin/scenarios/{sid}/versions/1", headers=w.alpha_h)).status_code == 404
    assert (await client.patch(f"/api/v1/admin/scenarios/{sid}", headers=w.alpha_h,
                               json={"is_active": False})).status_code == 404


async def test_assessment_flow(client, db_session, world, data, clock):
    w = world
    sid = await _publish(client, w.alpha_h, data)
    vid = (await _open_vacancy(client, w))["id"]
    for h in (w.shy_h, w.weak_h, w.strong_h):
        assert (await client.post(f"/api/v1/vacancies/{vid}/apply", headers=h, json={})).status_code == 201
    apps = {a["candidate"]["id"]: a["id"] for a in
            (await client.get(f"/api/v1/company/vacancies/{vid}/applications", headers=w.alpha_h)).json()}
    shy_app, weak_app, strong_app = apps[str(w.shy.id)], apps[str(w.weak.id)], apps[str(w.strong.id)]
    base = f"/api/v1/company/vacancies/{vid}/applications/{shy_app}/assessments"

    # boshqa kompaniya ssenariysi, noma'lum ssenariy, muddat chegarasi
    beta_sid = await _publish(client, w.beta_h, {**copy.deepcopy(data), "slug": "beta-sinov"})
    assert (await client.post(base, headers=w.alpha_h, json={"scenario_id": beta_sid})).status_code == 404
    assert (await client.post(base, headers=w.alpha_h, json={"scenario_id": str(uuid.uuid4())})).status_code == 404
    assert (await client.post(base, headers=w.alpha_h, json={"scenario_id": sid, "start_within_days": 15})).status_code == 422
    assert (await client.post(base, headers=w.beta_h, json={"scenario_id": sid})).status_code == 404

    r = await client.post(base, headers=w.alpha_h, json={"scenario_id": sid, "start_within_days": 3,
                                                         "note": "  Bir kunlik sinov  "})
    assert r.status_code == 201, r.text
    a = r.json()
    assert a["state"] == "assigned" and a["note"] == "Bir kunlik sinov" and a["result"] is None
    assert a["start_by"].startswith("2026-10-15T06:00")
    assert (await client.post(base, headers=w.alpha_h, json={"scenario_id": sid})).status_code == 409
    note = (await db_session.execute(select(Notification).where(Notification.kind == "assessment_assigned"))).scalar_one()
    assert note.user_id == w.shy.id and note.params["scenario"] == data["title"] and "15.10" in render(note)[1]

    detail = (await client.get(f"/api/v1/vacancies/{vid}", headers=w.shy_h)).json()
    assert [x["id"] for x in detail["assessments"]] == [a["id"]] and "result" not in detail["assessments"][0]

    start = f"/api/v1/vacancies/{vid}/assessments/{a['id']}/start"
    assert (await client.post(start, headers=w.weak_h)).status_code == 404
    r = await client.post(start, headers=w.shy_h)
    assert r.status_code == 200, r.text
    run_id = r.json()["run_id"]
    assert (await client.post(start, headers=w.shy_h)).status_code == 409
    assert run_id in {x["id"] for x in (await client.get("/api/v1/runs/my", headers=w.shy_h)).json()}
    assert (await client.post(base, headers=w.alpha_h, json={"scenario_id": sid})).status_code == 409   # tugamagan
    cancel = f"{base}/{a['id']}/cancel"
    assert (await client.post(cancel, headers=w.alpha_h)).status_code == 409                            # boshlangan

    def company_view():
        return client.get(f"/api/v1/company/vacancies/{vid}/applications", headers=w.alpha_h)

    view = {x["id"]: x for x in (await company_view()).json()}
    assert view[shy_app]["assessments"][0]["state"] == "in_progress"

    # Run tugadi → yakuniy hisobot: sertifikat yo'q, kompaniyaga natija va xabar
    run = await db_session.get(Run, uuid.UUID(run_id))
    run.status = RunStatus.COMPLETED
    await db_session.commit()
    assert await write_final_report(db_session, run.id, T0 + timedelta(hours=8), summarize=_final)
    await db_session.refresh(run)
    assert run.final_report["certificate"] is False
    assert await db_session.scalar(select(func.count()).select_from(Certificate)) == 0
    done = (await db_session.execute(select(Notification).where(Notification.kind == "assessment_completed"))).scalar_one()
    assert done.params["candidate"] == "Malika Tosheva" and done.link == f"/company/vacancies/{vid}"
    item = {x["id"]: x for x in (await company_view()).json()}[shy_app]["assessments"][0]
    assert item["state"] == "completed"
    assert item["result"]["summary"] == "Talaba buyurtmalar xatosini tez topdi." and item["result"]["strengths"] == ["Tahlil"]
    # profil (moslik, portfolio, hisobotlar) — faqat platforma Run'lari
    profile = (await build_profiles(db_session, [w.shy.id]))[w.shy.id]
    assert uuid.UUID(sid) not in {r.scenario_id for r in profile.runs}

    # muddati o'tgan: boshlab bo'lmaydi; bekor qilish faqat boshlanmaganni
    late = (await client.post(f"/api/v1/company/vacancies/{vid}/applications/{strong_app}/assessments",
                              headers=w.alpha_h, json={"scenario_id": sid, "start_within_days": 1})).json()
    clock[0] = T0 + timedelta(days=2)
    view = {x["id"]: x for x in (await company_view()).json()}
    assert view[strong_app]["assessments"][0]["state"] == "overdue"
    assert (await client.post(f"/api/v1/vacancies/{vid}/assessments/{late['id']}/start", headers=w.strong_h)).status_code == 409
    late_cancel = f"/api/v1/company/vacancies/{vid}/applications/{strong_app}/assessments/{late['id']}/cancel"
    assert (await client.post(late_cancel, headers=w.alpha_h)).json()["state"] == "cancelled"
    assert (await client.post(late_cancel, headers=w.alpha_h)).status_code == 409

    # qaytarib olish va rad etish kutayotgan sinovni bekor qiladi
    weak = (await client.post(f"/api/v1/company/vacancies/{vid}/applications/{weak_app}/assessments",
                              headers=w.alpha_h, json={"scenario_id": sid})).json()
    assert (await client.post(f"/api/v1/vacancies/{vid}/withdraw", headers=w.weak_h)).json()["status"] == "withdrawn"
    assert (await client.post(f"/api/v1/vacancies/{vid}/assessments/{weak['id']}/start", headers=w.weak_h)).status_code == 404
    assert (await client.post(f"/api/v1/vacancies/{vid}/apply", headers=w.weak_h, json={})).status_code == 201
    detail = (await client.get(f"/api/v1/vacancies/{vid}", headers=w.weak_h)).json()
    assert detail["assessments"][0]["state"] == "cancelled"

    again = (await client.post(f"/api/v1/company/vacancies/{vid}/applications/{strong_app}/assessments",
                               headers=w.alpha_h, json={"scenario_id": sid})).json()
    assert (await client.post(f"/api/v1/company/vacancies/{vid}/applications/{strong_app}/reject",
                              headers=w.alpha_h)).status_code == 200
    detail = (await client.get(f"/api/v1/vacancies/{vid}", headers=w.strong_h)).json()
    assert {x["id"]: x["state"] for x in detail["assessments"]}[again["id"]] == "cancelled"

    # nofaol ssenariy yuborilmaydi
    await client.patch(f"{URL}/{sid}", headers=w.alpha_h, json={"is_active": False})
    assert (await client.post(f"/api/v1/company/vacancies/{vid}/applications/{weak_app}/assessments",
                              headers=w.alpha_h, json={"scenario_id": sid})).status_code == 404
