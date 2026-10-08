"""
Kompaniya vakansiyalari (CONTRACT.md §23): moslik hisobi, maxfiylik, ariza oqimi.

Asosiy qoidalar: mos nomzodlar faqat §10 bo'yicha ko'rinadiganlardan; ariza —
rozilik (yopiq profil ham ariza ro'yxatida ko'rinadi), qaytarib olinsa — yo'q;
boshqa kompaniya vakansiyasi va qoralama — 404.
"""
import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.models.enums import ApplicationStatus, Sector, VacancyStatus
from app.models.notification import Notification
from app.models.talent import TalentOffer, Vacancy, VacancyApplication
from app.talent import vacancies as matching
from app.talent.profile import Profile, RunSummary
from tests.test_analytics import _scenario as _real_scenario
from tests.test_talent_hunt import NOW, _company, _hr, _run, _student

BODY = {
    "title": "Junior Backend dasturchi",
    "description": "Buyurtmalar xizmatini qo'llab-quvvatlash va yangi API'lar yozish.",
    "sector": "IT", "employment": "full_time", "work_format": "hybrid", "location": "Toshkent",
    "salary_min": 6_000_000, "salary_max": 9_000_000,
    "requirements": {"technical": 70, "communication": 60},
}


@pytest.fixture(autouse=True)
def _no_expire(db_session):
    db_session.sync_session.expire_on_commit = False


@pytest.fixture
async def world(client, db_session, test_user_factory):
    """Ikki kompaniya; uch nomzod: ochiq kuchli, ochiq zaif, yopiq (faqat ariza orqali)."""
    alpha = await _company(db_session, "Alpha")
    beta = await _company(db_session, "Beta")
    it = await _real_scenario(db_session, "it-day1", ["technical"])
    bank = await _real_scenario(db_session, "bank-day1", ["communication"], sector=Sector.BANKING)
    s = test_user_factory
    strong, strong_h = await _student(client, db_session, s, "strong@test.uz", "Dilnoza Karimova", open_to_work=True)
    weak, weak_h = await _student(client, db_session, s, "weak@test.uz", "Bekzod Aliyev", open_to_work=True)
    shy, shy_h = await _student(client, db_session, s, "shy@test.uz", "Malika Tosheva")       # yozuv yo'q — yopiq
    fresh, fresh_h = await _student(client, db_session, s, "fresh@test.uz", "Yangi Talaba", open_to_work=True)
    await _run(db_session, strong, it, score=84.0, competencies={"technical": 90.0, "communication": 72.0})
    await _run(db_session, weak, bank, score=41.0, competencies={"technical": 30.0, "communication": 25.0})
    await _run(db_session, shy, it, score=77.0, competencies={"technical": 80.0, "communication": 65.0})
    return SimpleNamespace(
        alpha=alpha, beta=beta, it=it, strong=strong, weak=weak, shy=shy, fresh=fresh,
        strong_h=strong_h, weak_h=weak_h, shy_h=shy_h, fresh_h=fresh_h,
        alpha_h=await _hr(client, db_session, s, alpha, "hr@alpha.test"),
        beta_h=await _hr(client, db_session, s, beta, "hr@beta.test"),
    )


async def _create(client, headers, **extra):
    return await client.post("/api/v1/company/vacancies", headers=headers, json={**BODY, **extra})


async def _open_vacancy(client, w, **extra):
    r = await _create(client, w.alpha_h, status="open", **extra)
    assert r.status_code == 201, r.text
    return r.json()


def _profile(overall, competencies, sector="IT"):
    run = RunSummary(
        run_id=uuid.uuid4(), scenario_id=uuid.uuid4(), scenario_title="x", company_name="x", sector=sector,
        completed_at=NOW, overall_score=overall, competency_scores=competencies, strengths=[],
    )
    return Profile(uuid.uuid4(), runs=[run])


# ── Moslik (sof funksiya) ────────────────────────────────────────────


def test_fit_rules():
    vacancy = Vacancy(requirements={"technical": 80, "communication": 50}, min_score=60, sector=Sector.IT)
    f = matching.fit(_profile(70.0, {"technical": 60.0, "communication": 90.0}), vacancy)
    assert f.fit == 87.5                                   # (60/80 + 1) / 2
    assert [(g.competency, g.required, g.actual) for g in f.gaps] == [("technical", 80, 60.0)]
    assert f.meets is False and f.sector_match is True

    f = matching.fit(_profile(55.0, {"technical": 85.0, "communication": 50.0}, sector="Data"), vacancy)
    assert f.fit == 100.0 and f.gaps == []
    assert f.meets is False                                # umumiy ball min_score'dan past
    assert f.sector_match is False

    f = matching.fit(_profile(65.0, {"technical": 85.0}), vacancy)
    assert f.fit == 50.0 and f.gaps[0].actual is None      # ma'lumot yo'q kompetensiya — 0

    open_vacancy = Vacancy(requirements={}, min_score=None, sector=Sector.IT)
    assert matching.fit(_profile(73.4, {}), open_vacancy).fit == 73.4
    assert matching.fit(Profile(uuid.uuid4()), open_vacancy).fit == 0.0
    zero = Vacancy(requirements={"initiative": 0}, min_score=None, sector=Sector.IT)
    assert matching.fit(_profile(10.0, {}), zero).meets is True


# ── Ruxsatlar ────────────────────────────────────────────────────────


async def test_permissions(client, db_session, test_user_factory, world):
    w = world
    assert (await client.get("/api/v1/company/vacancies")).status_code == 401
    assert (await client.get("/api/v1/company/vacancies", headers=w.strong_h)).status_code == 403
    assert (await client.get("/api/v1/vacancies", headers=w.alpha_h)).status_code == 403
    gamma = await _company(db_session, "Gamma", verified=False)
    gamma_h = await _hr(client, db_session, test_user_factory, gamma, "hr@gamma.test")
    assert (await _create(client, gamma_h)).status_code == 403

    vacancy = await _open_vacancy(client, w)
    for path in ("", "/matches", "/applications"):
        assert (await client.get(f"/api/v1/company/vacancies/{vacancy['id']}{path}", headers=w.beta_h)).status_code == 404
    assert (await client.put(f"/api/v1/company/vacancies/{vacancy['id']}", headers=w.beta_h, json=BODY)).status_code == 404


# ── Kompaniya: yaratish, tahrir, holat ───────────────────────────────


async def test_create_validate_and_status(client, db_session, world):
    w = world
    bad = [
        {"salary_min": 9_000_000, "salary_max": 1_000_000},
        {"requirements": {"technical": 120}},
        {"requirements": {"charisma": 50}},
        {"title": "  "},
        {"scenario_ids": [str(uuid.uuid4())]},
        {"requirements": {k: 50 for k in ("technical", "communication", "prioritization", "time_management",
                                         "stress_handling", "initiative")} | {"x": 1}},
    ]
    for extra in bad:
        assert (await _create(client, w.alpha_h, **extra)).status_code == 422, extra

    draft = (await _create(client, w.alpha_h, title="  Analitik  ", location=" ")).json()
    assert draft["status"] == "draft" and draft["published_at"] is None
    assert draft["title"] == "Analitik" and draft["location"] is None
    assert draft["counts"] == {"applications": 0, "new": 0, "matches": 1}      # kuchli nomzod talablarga yetadi

    url = f"/api/v1/company/vacancies/{draft['id']}"
    opened = (await client.post(f"{url}/status", headers=w.alpha_h, json={"status": "open"})).json()
    assert opened["status"] == "open" and opened["published_at"]
    closed = (await client.post(f"{url}/status", headers=w.alpha_h, json={"status": "closed"})).json()
    assert closed["status"] == "closed" and closed["closed_at"]
    reopened = (await client.post(f"{url}/status", headers=w.alpha_h, json={"status": "open"})).json()
    assert reopened["closed_at"] is None and reopened["published_at"] == opened["published_at"]
    assert (await client.post(f"{url}/status", headers=w.alpha_h, json={"status": "draft"})).status_code == 422

    edited = (await client.put(url, headers=w.alpha_h, json={**BODY, "requirements": {}, "min_score": 80})).json()
    assert edited["requirements"] == {} and edited["status"] == "open"
    assert edited["counts"]["matches"] == 1                                    # faqat 84 ballik

    listed = (await client.get("/api/v1/company/vacancies", headers=w.alpha_h)).json()
    assert [v["id"] for v in listed] == [draft["id"]]
    assert (await client.get("/api/v1/company/vacancies", headers=w.beta_h)).json() == []


async def test_open_limit(client, db_session, world):
    for i in range(matching_limit := 20):
        db_session.add(Vacancy(company_id=world.alpha.id, title=f"V{i}", description="x" * 20, sector=Sector.IT,
                               employment="full_time", work_format="office", status=VacancyStatus.OPEN,
                               created_at=NOW, updated_at=NOW))
    await db_session.commit()
    assert matching_limit == 20
    assert (await _create(client, world.alpha_h, status="open")).status_code == 409
    draft = (await _create(client, world.alpha_h)).json()
    r = await client.post(f"/api/v1/company/vacancies/{draft['id']}/status", headers=world.alpha_h, json={"status": "open"})
    assert r.status_code == 409
    assert (await _create(client, world.beta_h, status="open")).status_code == 201   # boshqa kompaniya limiti alohida


# ── Mos nomzodlar ────────────────────────────────────────────────────


async def test_matches_only_visible_candidates(client, db_session, world):
    w = world
    vacancy = await _open_vacancy(client, w)
    url = f"/api/v1/company/vacancies/{vacancy['id']}/matches"
    matches = (await client.get(url, headers=w.alpha_h)).json()
    # yopiq nomzod (shy) ko'rinmaydi; zaif — fit 42 < 50; profilsiz — yo'q
    assert [m["id"] for m in matches] == [str(w.strong.id)]
    m = matches[0]
    assert m["fit"] == {"fit": 100.0, "meets": True, "gaps": [], "sector_match": True} and m["applied"] is False
    assert "email" not in m

    # past talab — zaif nomzod ham chiqadi, mosroq tepada
    await client.put(f"/api/v1/company/vacancies/{vacancy['id']}", headers=w.alpha_h,
                     json={**BODY, "sector": "Banking", "requirements": {"technical": 50}})
    matches = (await client.get(url, headers=w.alpha_h)).json()
    assert [m["id"] for m in matches] == [str(w.strong.id), str(w.weak.id)]
    weak = matches[1]["fit"]
    assert weak["fit"] == 60.0 and weak["sector_match"] is True and weak["meets"] is False
    assert weak["gaps"] == [{"competency": "technical", "required": 50, "actual": 30.0}]


# ── Talaba: ro'yxat, ariza ───────────────────────────────────────────


async def test_student_sees_open_vacancies_with_fit(client, db_session, world):
    w = world
    vacancy = await _open_vacancy(client, w)
    draft = (await _create(client, w.alpha_h, title="Qoralama")).json()
    await _open_vacancy(client, w, title="Ma'lumotlar tahlilchisi", sector="Data", requirements={"technical": 95})
    gamma = await _company(db_session, "Gamma", verified=False)
    db_session.add(Vacancy(company_id=gamma.id, title="Tasdiqlanmagan", description="x" * 20, sector=Sector.IT,
                           employment="full_time", work_format="office", status=VacancyStatus.OPEN,
                           created_at=NOW, updated_at=NOW))
    await db_session.commit()

    items = (await client.get("/api/v1/vacancies", headers=w.strong_h)).json()
    assert [v["title"] for v in items] == ["Junior Backend dasturchi", "Ma'lumotlar tahlilchisi"]   # moslik bo'yicha
    assert items[0]["company"]["name"] == "Alpha" and items[0]["my_fit"]["fit"] == 100.0
    assert items[0]["application_status"] is None
    assert [v["title"] for v in (await client.get("/api/v1/vacancies?sector=Data", headers=w.strong_h)).json()] == [
        "Ma'lumotlar tahlilchisi"]
    # profilsiz talaba — moslik yo'q
    assert all(v["my_fit"] is None for v in (await client.get("/api/v1/vacancies", headers=w.fresh_h)).json())

    assert (await client.get(f"/api/v1/vacancies/{draft['id']}", headers=w.strong_h)).status_code == 404
    detail = (await client.get(f"/api/v1/vacancies/{vacancy['id']}", headers=w.weak_h)).json()
    assert detail["my_overall"] == 41.0 and detail["my_competencies"]["technical"] == 30.0
    assert [g["competency"] for g in detail["my_fit"]["gaps"]] == ["technical", "communication"]


async def test_apply_withdraw_and_company_view(client, db_session, world):
    w = world
    vacancy = await _open_vacancy(client, w)
    vid = vacancy["id"]
    apply_url = f"/api/v1/vacancies/{vid}/apply"
    apps_url = f"/api/v1/company/vacancies/{vid}/applications"

    assert (await client.post(apply_url, headers=w.fresh_h, json={})).status_code == 422   # tugatilgan Run yo'q
    r = await client.post(apply_url, headers=w.shy_h, json={"note": "  Backend menga yoqadi  "})
    assert r.status_code == 201 and r.json()["status"] == "applied" and r.json()["note"] == "Backend menga yoqadi"
    assert (await client.post(apply_url, headers=w.shy_h, json={})).status_code == 409

    # yopiq profil — mos nomzodlarda yo'q, arizada bor (rozilik)
    assert str(w.shy.id) not in {m["id"] for m in (await client.get(f"/api/v1/company/vacancies/{vid}/matches", headers=w.alpha_h)).json()}
    apps = (await client.get(apps_url, headers=w.alpha_h)).json()
    assert [(a["candidate"]["id"], a["status"], a["note"]) for a in apps] == [(str(w.shy.id), "applied", "Backend menga yoqadi")]
    assert apps[0]["fit"]["fit"] == pytest.approx(100.0) and "email" not in apps[0]["candidate"]
    assert (await client.get(f"/api/v1/company/vacancies/{vid}", headers=w.alpha_h)).json()["counts"]["new"] == 1

    notes = (await db_session.execute(select(Notification).where(Notification.kind == "application_received"))).scalars().all()
    assert len(notes) == 1 and notes[0].params["candidate"] == "Malika Tosheva"
    assert notes[0].link == f"/company/vacancies/{vid}"

    assert (await client.post(f"/api/v1/vacancies/{vid}/withdraw", headers=w.shy_h)).json()["status"] == "withdrawn"
    assert (await client.get(apps_url, headers=w.alpha_h)).json() == []
    assert (await client.post(f"/api/v1/vacancies/{vid}/withdraw", headers=w.shy_h)).status_code == 409

    # qayta ariza — o'sha qator, kompaniyaga qayta xabar yo'q
    assert (await client.post(apply_url, headers=w.shy_h, json={})).json()["status"] == "applied"
    db_session.expire_all()
    assert len((await db_session.execute(select(VacancyApplication))).scalars().all()) == 1
    assert len((await db_session.execute(select(Notification).where(Notification.kind == "application_received"))).scalars().all()) == 1

    # vakansiya yopildi — yangi ariza yo'q, ariza bergan talaba hali ko'radi
    await client.post(f"/api/v1/company/vacancies/{vid}/status", headers=w.alpha_h, json={"status": "closed"})
    assert (await client.post(apply_url, headers=w.strong_h, json={})).status_code == 404   # yopilgan — ariza bermaganga "yo'q"
    assert (await client.get(f"/api/v1/vacancies/{vid}", headers=w.strong_h)).status_code == 404
    assert (await client.get(f"/api/v1/vacancies/{vid}", headers=w.shy_h)).json()["application_status"] == "applied"
    assert (await client.get("/api/v1/vacancies", headers=w.shy_h)).json() == []

    mine = (await client.get("/api/v1/users/me/applications", headers=w.shy_h)).json()
    assert [(a["vacancy_title"], a["vacancy_status"], a["company_name"], a["status"]) for a in mine] == [
        ("Junior Backend dasturchi", "closed", "Alpha", "applied")]


async def test_reject_and_offer_from_application(client, db_session, world):
    w = world
    vid = (await _open_vacancy(client, w))["id"]
    for h in (w.shy_h, w.weak_h):
        assert (await client.post(f"/api/v1/vacancies/{vid}/apply", headers=h, json={})).status_code == 201
    apps = {a["candidate"]["id"]: a for a in (await client.get(f"/api/v1/company/vacancies/{vid}/applications", headers=w.alpha_h)).json()}
    shy_app, weak_app = apps[str(w.shy.id)], apps[str(w.weak.id)]

    reject = f"/api/v1/company/vacancies/{vid}/applications/{weak_app['id']}/reject"
    assert (await client.post(reject.replace(vid, str(uuid.uuid4())), headers=w.alpha_h)).status_code == 404
    assert (await client.post(reject, headers=w.beta_h)).status_code == 404
    assert (await client.post(reject, headers=w.alpha_h)).json()["status"] == "rejected"
    assert (await client.post(reject, headers=w.alpha_h)).status_code == 409
    note = (await db_session.execute(select(Notification).where(Notification.kind == "application_rejected"))).scalar_one()
    assert note.user_id == w.weak.id and note.params == {"vacancy_id": vid, "vacancy": BODY["title"], "company": "Alpha"}
    assert (await client.post(f"/api/v1/vacancies/{vid}/apply", headers=w.weak_h, json={})).status_code == 409

    offer = {"candidate_user_id": str(w.shy.id), "position_title": BODY["title"],
             "message": "Arizangizni ko'rdik, suhbatga taklif qilamiz."}
    # vakansiyasiz — yopiq profil 404 (§10), boshqa kompaniya vakansiyasi bilan ham
    assert (await client.post("/api/v1/talents/offers", headers=w.alpha_h, json=offer)).status_code == 404
    assert (await client.post("/api/v1/talents/offers", headers=w.beta_h, json={**offer, "vacancy_id": vid})).status_code == 404
    r = await client.post("/api/v1/talents/offers", headers=w.alpha_h, json={**offer, "vacancy_id": vid})
    assert r.status_code == 201 and r.json()["vacancy_id"] == vid

    db_session.expire_all()
    app_row = await db_session.get(VacancyApplication, uuid.UUID(shy_app["id"]))
    assert app_row.status == ApplicationStatus.OFFERED
    assert (await db_session.execute(select(TalentOffer))).scalar_one().vacancy_id == uuid.UUID(vid)
    # taklif yuborilgan ariza qaytarib olinmaydi va rad etilmaydi
    assert (await client.post(f"/api/v1/vacancies/{vid}/withdraw", headers=w.shy_h)).status_code == 409
    assert (await client.post(reject.replace(weak_app["id"], shy_app["id"]), headers=w.alpha_h)).status_code == 409
    counts = (await client.get(f"/api/v1/company/vacancies/{vid}", headers=w.alpha_h)).json()["counts"]
    assert counts["applications"] == 1 and counts["new"] == 0


# ── Mashq ssenariylari ───────────────────────────────────────────────


async def test_practice_scenarios(client, db_session, world):
    w = world
    await _real_scenario(db_session, "comm-day", ["communication"], sector=Sector.HR)
    tech = await _real_scenario(db_session, "tech-day", ["technical", "communication"])
    await _real_scenario(db_session, "other-day", ["initiative"])
    await _real_scenario(db_session, "hidden-day", ["technical"], active=False)
    await _run(db_session, w.weak, tech, score=40.0, competencies={"technical": 30.0})

    vacancy = await _open_vacancy(client, w, scenario_ids=[str(tech.scenario_id)])
    detail = (await client.get(f"/api/v1/vacancies/{vacancy['id']}", headers=w.weak_h)).json()
    assert [(p["title"], p["completed"], p["practices"]) for p in detail["practice"]] == [
        ("tech-day title", True, {"technical": 1, "communication": 1}),        # kompaniya tanlagani — birinchi
        ("it-day1 title", False, {"technical": 1}),                             # yetishmayotgan, vakansiya sohasi
        ("comm-day title", False, {"communication": 1}),
    ]                                                                           # bank-day1 — tugatilgan, faol emasi — yo'q
    # talabga yetgan talaba — faqat kompaniya tanlagani
    detail = (await client.get(f"/api/v1/vacancies/{vacancy['id']}", headers=w.strong_h)).json()
    assert [p["title"] for p in detail["practice"]] == ["tech-day title"]
