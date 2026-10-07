"""
Sertifikat va portfolio (CONTRACT.md §13).

Eng muhim qoidalar: sertifikat faqat tugagan Run uchun va bittadan;
ochiq tekshiruv va portfolio email/javoblarni bermaydi; portfolio default
yopiq va yopiq/yo'q slug bir xil 404; bekor qilingan sertifikatli ish
hech qaysi profilga kirmaydi.
"""
import pytest
from sqlalchemy import func, select

from app.credentials.issue import ALPHABET, issue_for_run, new_code, normalize_code
from app.credentials.slug import from_name
from app.models.billing import University
from app.models.credential import Certificate
from app.models.enums import RunStatus, Sector
from app.scenario.reports import write_final_report
from app.talent.profile import build_profiles
from tests.test_runs_engine import T, setup  # noqa: F401
from tests.test_runs_reports import _completed_run, _summarizers
from tests.test_talent_hunt import _headers, _run, _scenario, _student


@pytest.fixture(autouse=True)
def _no_expire(db_session):
    db_session.sync_session.expire_on_commit = False


async def _certified(db, user, version, **kw):
    run = await _run(db, user, version, **kw)
    await issue_for_run(db, run)
    await db.commit()
    return await db.scalar(select(Certificate).where(Certificate.run_id == run.id))


@pytest.fixture
async def world(client, db_session, test_user_factory):
    """Ikki sertifikatli talaba (Bank, IT), universitet, admin."""
    uni = University(name="Samdu", city="Samarqand", contact_email="info@samdu.uz", is_verified=True)
    db_session.add(uni)
    await db_session.commit()
    aziza, aziza_h = await _student(client, db_session, test_user_factory, "aziza@test.uz", "Aziza O'ktamova")
    aziza.university_id = uni.id
    await db_session.commit()
    it = await _scenario(db_session, "it-day1")
    bank = await _scenario(db_session, "bank-day1", Sector.BANKING)
    old = await _certified(db_session, aziza, it, score=70.0, competencies={"technical": 60.0}, days_ago=5)
    new = await _certified(db_session, aziza, bank, score=90.0, competencies={"technical": 90.0, "communication": 80.0})

    await test_user_factory("admin@test.uz", "pass", "admin")
    return {"aziza": aziza, "aziza_h": aziza_h, "old": old, "new": new, "it": it,
            "admin_h": await _headers(client, "admin@test.uz")}


# ── Berish ───────────────────────────────────────────────────────────


async def test_final_report_issues_one_certificate(db_session, setup):  # noqa: F811
    run = await _completed_run(db_session, setup)
    _, final, _ = _summarizers()
    assert await write_final_report(db_session, run.id, T("17:41"), summarize=final)
    assert await write_final_report(db_session, run.id, T("18:00"), summarize=final)   # qayta — yangi yo'q
    await issue_for_run(db_session, run)
    await db_session.commit()

    [cert] = (await db_session.execute(select(Certificate).where(Certificate.run_id == run.id))).scalars().all()
    await db_session.refresh(run)
    assert cert.user_id == run.user_id and cert.overall_score == run.final_report["overall_score"] == 80.0
    assert cert.competency_scores == run.competency_scores
    assert normalize_code(cert.code) == cert.code and cert.revoked_at is None


async def test_no_certificate_without_completion(db_session, test_user_factory):
    user = await test_user_factory("late@test.uz", "pass")
    version = await _scenario(db_session, "it-day1")
    for status in (RunStatus.EXPIRED, RunStatus.ABANDONED):
        run = await _run(db_session, user, version, score=50.0, competencies={}, status=status)
        await issue_for_run(db_session, run)
    await db_session.commit()
    assert await db_session.scalar(select(func.count()).select_from(Certificate)) == 0


def test_code_format():
    code = new_code()
    assert code[:3] == "TJ-" and code[7] == "-" and set(code[3:7] + code[8:]) <= set(ALPHABET)
    assert normalize_code(f" {code.lower().replace('-', ' ')} ") == code
    assert normalize_code(code.replace("-", "")) == code
    for bad in ("TJ-0000-0000", "TJ-ABCD-EFG", "XX-ABCD-EFGH", "", "TJ-ABCD-EFGH-J"):
        assert normalize_code(bad) is None, bad


def test_slug_from_name():
    assert from_name("O'tkir G‘ulomov") == "otkir-gulomov"
    assert from_name("  Ali  Valiyev-Jr. ") == "ali-valiyev-jr"
    assert from_name("Шаҳноза Ўринова") == "shahnoza-orinova"
    assert from_name("李") == "talaba"


# ── Ochiq tekshiruv ──────────────────────────────────────────────────


async def test_verify_certificate_is_public(client, world):
    cert = world["new"]
    r = await client.get(f"/api/v1/certificates/{cert.code.lower().replace('-', '')}")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "valid" and data["code"] == cert.code
    assert (data["holder_name"], data["scenario_title"], data["sector"]) == (
        "Aziza O'ktamova", "bank-day1 title", "Banking")
    assert data["overall_score"] == 90.0 and data["competency_scores"] == {"technical": 90.0, "communication": 80.0}
    assert not {"email", "run_id", "user_id", "final_report"} & set(data)

    for missing in ("TJ-2222-2222", "nonsense"):
        assert (await client.get(f"/api/v1/certificates/{missing}")).status_code == 404


async def test_certificate_is_a_snapshot(client, db_session, world):
    world["aziza"].full_name = "Aziza Boshqa"
    await db_session.commit()
    data = (await client.get(f"/api/v1/certificates/{world['new'].code}")).json()
    assert data["holder_name"] == "Aziza O'ktamova"


async def test_my_certificates(client, world):
    data = (await client.get("/api/v1/users/me/certificates", headers=world["aziza_h"])).json()
    assert [c["code"] for c in data] == [world["new"].code, world["old"].code]
    assert data[0]["run_id"] == str(world["new"].run_id)
    assert (await client.get("/api/v1/users/me/certificates", headers=world["admin_h"])).status_code == 403
    assert (await client.get("/api/v1/users/me/certificates")).status_code == 401


# ── Bekor qilish ─────────────────────────────────────────────────────


async def test_revoke(client, db_session, world):
    code = world["old"].code
    url = f"/api/v1/admin/certificates/{code}/revoke"
    assert (await client.post(url, json={"reason": "Ko'chirilgan"}, headers=world["aziza_h"])).status_code == 403
    assert (await client.post(url, json={"reason": ""}, headers=world["admin_h"])).status_code == 422

    r = await client.post(url, json={"reason": "  Javoblar ko'chirilgan  "}, headers=world["admin_h"])
    assert r.status_code == 200 and r.json()["status"] == "revoked"
    assert (await client.post(url, json={"reason": "yana"}, headers=world["admin_h"])).status_code == 409
    assert (await client.post("/api/v1/admin/certificates/TJ-2222-2222/revoke", json={"reason": "yo'q"},
                              headers=world["admin_h"])).status_code == 404

    data = (await client.get(f"/api/v1/certificates/{code}")).json()
    assert data["status"] == "revoked" and data["revoked_reason"] == "Javoblar ko'chirilgan"
    # profil (kompaniya, universitet, portfolio) — faqat bekor qilinmagan ish
    profile = (await build_profiles(db_session, [world["aziza"].id]))[world["aziza"].id]
    assert [r.scenario_title for r in profile.runs] == ["bank-day1 title"]


# ── Portfolio ────────────────────────────────────────────────────────


async def _publish(client, headers, **overrides):
    body = {"slug": "aziza", "is_public": True, "headline": "Junior kredit tahlilchisi",
            "about": "Bank va IT ssenariylari", "links": [{"label": "GitHub", "url": "https://github.com/aziza"}]}
    return await client.put("/api/v1/users/me/portfolio", headers=headers, json={**body, **overrides})


async def test_portfolio_defaults_to_private(client, db_session, test_user_factory, world):
    settings = (await client.get("/api/v1/users/me/portfolio", headers=world["aziza_h"])).json()
    assert settings == {"slug": "aziza-oktamova", "is_public": False, "headline": "", "about": "",
                        "links": [], "exists": False}
    # band slug'ga raqam qo'shiladi
    _, other_h = await _student(client, db_session, test_user_factory, "other@test.uz", "Aziza O'ktamova")
    assert (await _publish(client, other_h, slug="aziza-oktamova")).status_code == 200
    settings = (await client.get("/api/v1/users/me/portfolio", headers=world["aziza_h"])).json()
    assert settings["slug"] == "aziza-oktamova-2"


async def test_public_portfolio(client, world):
    assert (await client.get("/api/v1/portfolios/aziza")).status_code == 404
    r = await _publish(client, world["aziza_h"], slug="Aziza", is_public=False)
    assert r.status_code == 200 and r.json()["slug"] == "aziza" and r.json()["exists"]
    assert (await client.get("/api/v1/portfolios/aziza")).status_code == 404   # yopiq — yo'q bilan bir xil

    await _publish(client, world["aziza_h"])
    data = (await client.get("/api/v1/portfolios/AZIZA")).json()
    assert (data["full_name"], data["headline"]) == ("Aziza O'ktamova", "Junior kredit tahlilchisi")
    assert data["links"] == [{"label": "GitHub", "url": "https://github.com/aziza"}]
    assert data["university"] == {"name": "Samdu", "city": "Samarqand"}
    assert data["overall_score"] == 80.0 and data["sectors"] == ["Banking", "IT"]
    assert [c["code"] for c in data["certificates"]] == [world["new"].code, world["old"].code]
    assert "email" not in str(data) and "aziza@test.uz" not in str(data)


async def test_public_portfolio_hides_revoked(client, world):
    await _publish(client, world["aziza_h"])
    await client.post(f"/api/v1/admin/certificates/{world['old'].code}/revoke", json={"reason": "Ko'chirilgan"},
                      headers=world["admin_h"])
    data = (await client.get("/api/v1/portfolios/aziza")).json()
    assert [c["code"] for c in data["certificates"]] == [world["new"].code]
    assert data["overall_score"] == 90.0 and data["sectors"] == ["Banking"]


async def test_portfolio_validation(client, db_session, test_user_factory, world):
    h = world["aziza_h"]
    for bad in (
        {"slug": "a"}, {"slug": "-aziza"}, {"slug": "aziza karimova"}, {"slug": "a" * 41},
        {"links": [{"label": "Sayt", "url": "http://aziza.uz"}]},
        {"links": [{"label": "Skript", "url": "javascript:alert(1)"}]},
        {"links": [{"label": " ", "url": "https://aziza.uz"}]},
        {"links": [{"label": f"L{i}", "url": f"https://x.uz/{i}"} for i in range(4)]},
        {"headline": "x" * 121}, {"about": "x" * 1001},
    ):
        assert (await _publish(client, h, **bad)).status_code == 422, bad

    _, other_h = await _student(client, db_session, test_user_factory, "other@test.uz", "Boshqa Talaba")
    assert (await _publish(client, other_h, slug="aziza")).status_code == 200
    assert (await _publish(client, h, slug="aziza")).status_code == 409
    assert (await client.put("/api/v1/users/me/portfolio", headers=world["admin_h"],
                             json={"slug": "admin", "is_public": True})).status_code == 403


async def test_inactive_user_portfolio_is_hidden(client, db_session, world):
    await _publish(client, world["aziza_h"])
    world["aziza"].is_active = False
    await db_session.commit()
    assert (await client.get("/api/v1/portfolios/aziza")).status_code == 404
