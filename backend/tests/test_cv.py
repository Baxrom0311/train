"""
Talaba CV'si (CONTRACT.md §28).

Eng muhim qoidalar: CV §10.1 profilidan (kompaniya sinovi va bekor
qilingan sertifikatli ish kirmaydi, har ssenariydan eng yaxshisi);
yashirish faqat yozuvni tushiradi, ballarni emas; boshqaning Run'ini
yashirib bo'lmaydi; CV faqat egasiga.
"""
import pytest
from sqlalchemy import select

from app.credentials.cv import task_counts, top_competencies
from app.credentials.issue import issue_for_run
from app.models.billing import University
from app.models.credential import Certificate, Portfolio
from app.models.enums import Sector
from app.models.scenario import Scenario
from tests.test_talent_hunt import _company, _headers, _hr, _run, _scenario, _student


URL = "/api/v1/users/me/cv"


@pytest.fixture(autouse=True)
def _no_expire(db_session):
    db_session.sync_session.expire_on_commit = False


def _task(status, late=False):
    return {"status": status, "late": late, "title": "Vazifa", "score": 80.0}


async def _detailed(db, user, version, *, certify=True, **kw):
    """Yakuniy hisobotida vazifalar va o'z vaqtida foizi bor Run."""
    run = await _run(db, user, version, **kw)
    run.final_report = {
        **run.final_report,
        "on_time_rate": 66.7,
        "tasks": [_task("submitted"), _task("submitted", late=True), _task("missed"), _task("skipped"), _task("pending")],
        "summary": {"summary": "Yaxshi", "strengths": ["Aniq yozadi", "Tez", "Savol beradi", "Tartibli"], "improvements": []},
    }
    if certify:
        await issue_for_run(db, run)
    await db.commit()
    return run


@pytest.fixture
async def world(client, db_session, test_user_factory):
    """Universitetli talaba: IT (ikki urinish), Bank, bekor qilingan Marketing va kompaniya sinovi."""
    uni = University(name="Samdu", city="Samarqand", contact_email="info@samdu.uz", is_verified=True)
    db_session.add(uni)
    await db_session.commit()
    aziza, aziza_h = await _student(client, db_session, test_user_factory, "aziza@test.uz", "Aziza O'ktamova")
    aziza.university_id = uni.id
    await db_session.commit()

    it = await _scenario(db_session, "it-day1")
    bank = await _scenario(db_session, "bank-day1", Sector.BANKING)
    mkt = await _scenario(db_session, "mkt-day1", Sector.MARKETING)
    trial = await _scenario(db_session, "alpha-trial")
    alpha = await _company(db_session, "Alpha")
    (await db_session.get(Scenario, trial.scenario_id)).owner_company_id = alpha.id
    await db_session.commit()

    weak_it = await _run(db_session, aziza, it, score=55.0, competencies={"technical": 50.0}, days_ago=9)
    best_it = await _detailed(db_session, aziza, it, score=85.0, days_ago=6,
                              competencies={"technical": 90.0, "communication": 70.0, "teamwork": 70.0, "initiative": 60.0})
    bank_run = await _detailed(db_session, aziza, bank, score=75.0, competencies={"communication": 80.0}, days_ago=2,
                               certify=False)
    revoked = await _detailed(db_session, aziza, mkt, score=99.0, competencies={"creativity": 99.0}, days_ago=4)
    cert = await db_session.scalar(select(Certificate).where(Certificate.run_id == revoked.id))
    cert.revoked_at, cert.revoked_reason = best_it.last_activity_at, "Ko'chirilgan"
    await _run(db_session, aziza, trial, score=100.0, competencies={"technical": 100.0}, days_ago=1)
    await db_session.commit()
    return {"aziza": aziza, "h": aziza_h, "weak_it": weak_it, "best_it": best_it, "bank": bank_run, "alpha": alpha}


# ── Sof funksiyalar ──────────────────────────────────────────────────


def test_task_counts_use_on_time_denominator():
    tasks = [_task("submitted"), _task("submitted", late=True), _task("missed"), _task("skipped"), _task("delivered")]
    assert task_counts(tasks) == (2, 3)
    assert task_counts([]) == (0, 0)


def test_top_competencies_are_stable():
    assert top_competencies({"b": 70.0, "a": 70.0, "c": 90.0, "d": 10.0}) == {"c": 90.0, "a": 70.0, "b": 70.0}


# ── GET /me/cv ───────────────────────────────────────────────────────


async def test_empty_cv(client, db_session, test_user_factory):
    _, h = await _student(client, db_session, test_user_factory, "new@test.uz", "Yangi Talaba")
    data = (await client.get(URL, headers=h)).json()
    assert data["full_name"] == "Yangi Talaba" and data["email"] == "new@test.uz"
    assert data["experience"] == [] and data["overall_score"] is None and data["competencies"] == {}
    assert data["headline"] == "" and data["links"] == [] and data["portfolio_slug"] is None and data["university"] is None
    assert data["settings"] == {"phone": None, "city": None, "languages": [], "hidden_run_ids": []}


async def test_cv_is_built_from_profile(client, world):
    data = (await client.get(URL, headers=world["h"])).json()

    # bekor qilingan Marketing va kompaniya sinovi yo'q; IT — eng yaxshi urinish; yangisi birinchi
    assert [e["run_id"] for e in data["experience"]] == [str(world["bank"].id), str(world["best_it"].id)]
    assert data["sectors"] == ["Banking", "IT"]
    assert data["overall_score"] == 80.0   # (85 + 75) / 2 — §10.1 profili
    assert list(data["competencies"]) == ["technical", "communication", "teamwork", "initiative"]
    assert data["university"] == {"name": "Samdu", "city": "Samarqand"}

    bank, it = data["experience"]
    assert bank["certificate_code"] is None   # sertifikatsiz
    cert = it["certificate_code"]
    assert cert and cert.startswith("TJ-")
    assert it["company_name"] == "Lazurit Go" and it["difficulty"] == "junior" and it["duration_days"] == 1
    assert it["tasks_submitted"] == 2 and it["tasks_total"] == 3 and it["on_time_rate"] == 66.7
    assert it["top_competencies"] == {"technical": 90.0, "communication": 70.0, "teamwork": 70.0}
    assert it["strengths"] == ["Aniq yozadi", "Tez", "Savol beradi"]
    assert it["started_at"] < it["completed_at"] and it["hidden"] is False


async def test_old_run_without_task_details(client, db_session, test_user_factory):
    """Hisobotida `tasks` va `on_time_rate` yo'q eski Run ham CV'ni buzmaydi."""
    user, h = await _student(client, db_session, test_user_factory, "old@test.uz", "Eski Talaba")
    await _run(db_session, user, await _scenario(db_session, "it-old"), score=70.0, competencies={})
    [entry] = (await client.get(URL, headers=h)).json()["experience"]
    assert (entry["tasks_submitted"], entry["tasks_total"], entry["on_time_rate"]) == (0, 0, None)
    assert entry["top_competencies"] == {} and entry["strengths"] == ["Aniq yozadi"]


async def test_portfolio_fields(client, db_session, world):
    portfolio = Portfolio(user_id=world["aziza"].id, slug="aziza", is_public=False, headline="Junior backend",
                          about="Go va SQL", links=[{"label": "GitHub", "url": "https://github.com/aziza-demo"}])
    db_session.add(portfolio)
    await db_session.commit()
    data = (await client.get(URL, headers=world["h"])).json()
    assert data["headline"] == "Junior backend" and data["about"] == "Go va SQL"
    assert data["links"] == [{"label": "GitHub", "url": "https://github.com/aziza-demo"}]
    assert data["portfolio_slug"] is None   # yopiq portfolio havolasi CV'ga chiqmaydi

    portfolio.is_public = True
    await db_session.commit()
    assert (await client.get(URL, headers=world["h"])).json()["portfolio_slug"] == "aziza"


# ── PUT /me/cv/settings ──────────────────────────────────────────────


async def test_save_settings(client, db_session, test_user_factory, world):
    other, _ = await _student(client, db_session, test_user_factory, "other@test.uz", "Boshqa Talaba")
    foreign = await _run(db_session, other, await _scenario(db_session, "it-other"), score=50.0, competencies={})
    body = {
        "phone": "  +998 90 123-45-67 ", "city": "  Samarqand  ",
        "languages": ["O'zbek tili — ona tili", "Ingliz tili  —  B2", "ingliz tili — b2"],
        "hidden_run_ids": [str(world["bank"].id), str(foreign.id), str(world["bank"].id)],
    }
    r = await client.put(f"{URL}/settings", json=body, headers=world["h"])
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["settings"] == {
        "phone": "+998 90 123-45-67", "city": "Samarqand",
        "languages": ["O'zbek tili — ona tili", "Ingliz tili — B2"],
        "hidden_run_ids": [str(world["bank"].id)],   # boshqaning Run'i va takror tashlandi
    }
    bank, it = data["experience"]
    assert bank["hidden"] is True and it["hidden"] is False
    # yashirish ballarga tegmaydi (§28.1)
    assert data["overall_score"] == 80.0 and data["sectors"] == ["Banking", "IT"]

    # qayta saqlash — ustidan yoziladi, bo'sh maydonlar tozalanadi
    r = await client.put(f"{URL}/settings", json={"phone": "", "city": None, "languages": [], "hidden_run_ids": []},
                         headers=world["h"])
    assert r.json()["settings"] == {"phone": None, "city": None, "languages": [], "hidden_run_ids": []}
    assert (await client.get(URL, headers=world["h"])).json()["experience"][0]["hidden"] is False


@pytest.mark.parametrize("body", [
    {"phone": "+998 abc"},
    {"phone": "12-34"},                       # 7 raqamdan kam
    {"phone": "+998 90 123 45 67 89 00 11"},  # 20 belgidan uzun
    {"city": "x" * 81},
    {"languages": ["a"] * 6},
    {"languages": ["x" * 41]},
    {"languages": ["   "]},
    {"hidden_run_ids": ["not-a-uuid"]},
])
async def test_settings_validation(client, world, body):
    r = await client.put(f"{URL}/settings", json=body, headers=world["h"])
    assert r.status_code == 422


# ── Ruxsat ───────────────────────────────────────────────────────────


async def test_cv_is_owner_only(client, db_session, test_user_factory, world):
    assert (await client.get(URL)).status_code == 401
    hr_h = await _hr(client, db_session, test_user_factory, world["alpha"], "hr@alpha.test")
    assert (await client.get(URL, headers=hr_h)).status_code == 403
    assert (await client.put(f"{URL}/settings", json={}, headers=hr_h)).status_code == 403


async def test_cv_settings_do_not_leak_to_public_portfolio(client, db_session, world):
    db_session.add(Portfolio(user_id=world["aziza"].id, slug="aziza", is_public=True))
    await db_session.commit()
    await client.put(f"{URL}/settings", json={"phone": "+998901234567", "city": "Samarqand"}, headers=world["h"])
    public = (await client.get("/api/v1/portfolios/aziza")).json()
    assert "+998901234567" not in str(public) and "aziza@test.uz" not in str(public)

