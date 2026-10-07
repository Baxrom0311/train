"""
Talent Hunt (CONTRACT.md §5 maxfiylik, §10 Run natijalari va takliflar).

Eng muhim qoida: yozuv yo'q / yopiq / kompaniya yashirilgan nomzod kompaniya
uchun mavjud emas — ro'yxatda ham, profilda ham, taklifda ham (404, 403 emas).
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.billing import Company
from app.models.enums import RunStatus, ScenarioVersionStatus, Sector, TalentOfferStatus
from app.models.scenario import Run, Scenario, ScenarioVersion
from app.models.talent import CandidateVisibility, TalentOffer
from app.models.user import User
from app.scenario.clock import WorkCalendar

pytestmark = pytest.mark.asyncio

NOW = datetime.now(timezone.utc)


# ── Yordamchilar ─────────────────────────────────────────────────────


async def _headers(client, email):
    r = await client.post("/api/v1/auth/login", data={"username": email, "password": "pass"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _company(db, name, verified=True):
    company = Company(name=name, industry="Fintech", contact_email=f"hr@{name.lower()}.test", is_verified=verified)
    db.add(company)
    await db.commit()
    return company


async def _hr(client, db, factory, company, email):
    user = await factory(email, "pass", "company_hr")
    user.org_type = "company"
    user.org_id = company.id
    await db.commit()
    return await _headers(client, email)


async def _student(client, db, factory, email, name, *, open_to_work=None, hidden=()):
    user = await factory(email, "pass", "student")
    user.full_name = name
    if open_to_work is not None:
        db.add(CandidateVisibility(
            user_id=user.id, is_open_to_work=open_to_work, hidden_from_company_ids=[str(c) for c in hidden],
        ))
    await db.commit()
    return user, await _headers(client, email)


async def _scenario(db, slug, sector=Sector.IT):
    scenario = Scenario(
        slug=slug, title=f"{slug} title", sector=sector, company_name="Lazurit Go",
        difficulty="junior", duration_days=1,
    )
    version = ScenarioVersion(scenario=scenario, version=1, status=ScenarioVersionStatus.PUBLISHED, definition={})
    db.add_all([scenario, version])
    await db.commit()
    return version


async def _run(db, user, version, *, score, competencies, status=RunStatus.COMPLETED, days_ago=1):
    at = NOW - timedelta(days=days_ago)
    run = Run(
        user_id=user.id, scenario_version_id=version.id, status=status,
        start_at=at - timedelta(hours=8), ends_at=at, last_activity_at=at,
        competency_scores=competencies,
        final_report={
            "overall_score": score, "certificate": status == RunStatus.COMPLETED,
            "summary": {"summary": "Yaxshi", "strengths": ["Aniq yozadi"], "improvements": []},
        },
    )
    db.add(run)
    await db.commit()
    return run


@pytest.fixture(autouse=True)
def _no_expire(db_session):
    db_session.sync_session.expire_on_commit = False


@pytest.fixture
async def world(client, db_session, test_user_factory):
    """Ikki kompaniya, IT ssenariysi, profili bor ochiq nomzod."""
    alpha = await _company(db_session, "Alpha")
    beta = await _company(db_session, "Beta")
    it = await _scenario(db_session, "it-day1")
    cand, cand_h = await _student(client, db_session, test_user_factory, "cand@test.uz", "Dilnoza Karimova", open_to_work=True)
    await _run(db_session, cand, it, score=82.0, competencies={"technical": 90.0, "communication": 70.0})
    return {
        "alpha": alpha, "beta": beta, "it": it, "cand": cand, "cand_h": cand_h,
        "alpha_h": await _hr(client, db_session, test_user_factory, alpha, "hr@alpha.test"),
        "beta_h": await _hr(client, db_session, test_user_factory, beta, "hr@beta.test"),
    }


async def _offer(client, w, headers=None, **extra):
    body = {"candidate_user_id": str(w["cand"].id), "position_title": "Junior Backend",
            "message": "Ishingiz yoqdi, suhbatga taklif qilamiz.", **extra}
    return await client.post("/api/v1/talents/offers", json=body, headers=headers or w["alpha_h"])


def _ids(res):
    return {c["id"] for c in res.json()["items"]}


# ── Ruxsatlar ────────────────────────────────────────────────────────


async def test_me_lists_permissions(client, world):
    me = (await client.get("/api/v1/users/me", headers=world["cand_h"])).json()
    assert me["permissions"] == ["join_university", "receive_offers"]
    me = (await client.get("/api/v1/users/me", headers=world["alpha_h"])).json()
    assert me["permissions"] == ["view_candidates", "view_org_invoices"]


async def test_students_and_unverified_companies_cannot_browse(client, db_session, test_user_factory, world):
    assert (await client.get("/api/v1/talents", headers=world["cand_h"])).status_code == 403
    gamma = await _company(db_session, "Gamma", verified=False)
    gamma_h = await _hr(client, db_session, test_user_factory, gamma, "hr@gamma.test")
    assert (await client.get("/api/v1/talents", headers=gamma_h)).status_code == 403
    assert (await _offer(client, world, gamma_h)).status_code == 403
    # kompaniya xodimi talaba endpointlariga kira olmaydi
    assert (await client.get("/api/v1/talents/offers/my", headers=world["alpha_h"])).status_code == 403


# ── Maxfiylik ────────────────────────────────────────────────────────


async def test_visibility_is_opt_in(client, db_session, test_user_factory, world):
    """Yozuvi yo'q va yopiq nomzod Run natijasi bo'lsa ham ko'rinmaydi."""
    silent, silent_h = await _student(client, db_session, test_user_factory, "silent@test.uz", "Silent")
    closed, _ = await _student(client, db_session, test_user_factory, "closed@test.uz", "Closed", open_to_work=False)
    for u in (silent, closed):
        await _run(db_session, u, world["it"], score=95.0, competencies={"technical": 95.0})

    ids = _ids(await client.get("/api/v1/talents", headers=world["alpha_h"]))
    assert ids == {str(world["cand"].id)}
    assert (await client.get(f"/api/v1/talents/{silent.id}", headers=world["alpha_h"])).status_code == 404

    assert (await client.get("/api/v1/users/me/visibility", headers=silent_h)).json() == {
        "is_open_to_work": False, "hidden_from_company_ids": []
    }
    r = await client.patch("/api/v1/users/me/visibility", headers=silent_h, json={"is_open_to_work": True})
    assert r.status_code == 200 and r.json()["is_open_to_work"] is True
    assert str(silent.id) in _ids(await client.get("/api/v1/talents", headers=world["alpha_h"]))


async def test_hidden_company_sees_nothing(client, world):
    w = world
    r = await client.patch("/api/v1/users/me/visibility", headers=w["cand_h"],
                           json={"is_open_to_work": True, "hidden_from_company_ids": [str(w["alpha"].id)] * 2})
    assert r.json()["hidden_from_company_ids"] == [str(w["alpha"].id)]  # takrorlar olib tashlanadi

    assert _ids(await client.get("/api/v1/talents", headers=w["alpha_h"])) == set()
    assert (await client.get(f"/api/v1/talents/{w['cand'].id}", headers=w["alpha_h"])).status_code == 404
    assert (await _offer(client, w)).status_code == 404
    # boshqa kompaniya ko'radi
    assert _ids(await client.get("/api/v1/talents", headers=w["beta_h"])) == {str(w["cand"].id)}


async def test_candidate_without_completed_run_is_not_listed(client, db_session, test_user_factory, world):
    fresh, _ = await _student(client, db_session, test_user_factory, "fresh@test.uz", "Fresh", open_to_work=True)
    await _run(db_session, fresh, world["it"], score=99.0, competencies={"technical": 99.0}, status=RunStatus.EXPIRED)
    assert str(fresh.id) not in _ids(await client.get("/api/v1/talents", headers=world["alpha_h"]))
    assert (await _offer(client, world | {"cand": fresh})).status_code == 404


# ── Profil ───────────────────────────────────────────────────────────


async def test_profile_uses_best_completed_run_per_scenario(client, db_session, world):
    w = world
    bank = await _scenario(db_session, "bank-day1", Sector.BANKING)
    # IT qayta o'tilgan: yomonrog'i e'tiborga olinmaydi; tugallanmagan Run kirmaydi
    await _run(db_session, w["cand"], w["it"], score=60.0, competencies={"technical": 50.0}, days_ago=0)
    await _run(db_session, w["cand"], bank, score=70.0, competencies={"technical": 60.0, "prioritization": 80.0})
    await _run(db_session, w["cand"], bank, score=100.0, competencies={"technical": 100.0}, status=RunStatus.ABANDONED)

    p = (await client.get(f"/api/v1/talents/{w['cand'].id}", headers=w["alpha_h"])).json()
    assert p["runs_completed"] == 2
    assert p["overall_score"] == 76.0
    assert p["competencies"] == {"communication": 70.0, "prioritization": 80.0, "technical": 75.0}
    assert list(p["top_competencies"]) == ["prioritization", "technical", "communication"]
    assert p["sectors"] == ["Banking", "IT"]
    assert {r["overall_score"] for r in p["runs"]} == {82.0, 70.0}
    assert p["runs"][0]["strengths"] == ["Aniq yozadi"]
    assert "email" not in p

    me = (await client.get("/api/v1/users/me/talent-profile", headers=w["cand_h"])).json()
    assert me["overall_score"] == 76.0


async def test_filters_and_sorting(client, db_session, test_user_factory, world):
    w = world
    bank = await _scenario(db_session, "bank-day1", Sector.BANKING)
    other, _ = await _student(client, db_session, test_user_factory, "other@test.uz", "Other", open_to_work=True)
    await _run(db_session, other, bank, score=65.0, competencies={"communication": 95.0}, days_ago=0)
    h = w["alpha_h"]

    items = (await client.get("/api/v1/talents", headers=h)).json()["items"]
    assert [c["full_name"] for c in items] == ["Dilnoza Karimova", "Other"]
    items = (await client.get("/api/v1/talents?sort=recent", headers=h)).json()["items"]
    assert [c["full_name"] for c in items] == ["Other", "Dilnoza Karimova"]
    items = (await client.get("/api/v1/talents?competency=communication", headers=h)).json()["items"]
    assert [c["full_name"] for c in items] == ["Other", "Dilnoza Karimova"]

    assert _ids(await client.get("/api/v1/talents?sector=Banking", headers=h)) == {str(other.id)}
    assert _ids(await client.get("/api/v1/talents?min_score=80", headers=h)) == {str(w["cand"].id)}
    page = (await client.get("/api/v1/talents?limit=1&offset=1", headers=h)).json()
    assert page["total"] == 2 and len(page["items"]) == 1
    assert (await client.get("/api/v1/talents?competency=nonsense", headers=h)).status_code == 422


# ── Takliflar ────────────────────────────────────────────────────────


async def test_offer_flow_reveals_contact_only_after_accept(client, world):
    w = world
    r = await _offer(client, w)
    assert r.status_code == 201
    offer = r.json()
    expected_due = WorkCalendar().add_work_minutes(
        datetime.fromisoformat(offer["created_at"]), 5 * WorkCalendar().minutes_per_day
    )
    assert datetime.fromisoformat(offer["respond_due_at"]) == expected_due
    assert (await _offer(client, w)).status_code == 409  # javob kutilmoqda

    sent = (await client.get("/api/v1/talents/offers/sent", headers=w["alpha_h"])).json()
    assert sent[0]["candidate_name"] == "Dilnoza Karimova" and sent[0]["candidate_email"] is None

    mine = (await client.get("/api/v1/talents/offers/my", headers=w["cand_h"])).json()
    assert mine[0]["company_name"] == "Alpha" and mine[0]["status"] == "sent"
    r = await client.post(f"/api/v1/talents/offers/{offer['id']}/view", headers=w["cand_h"])
    assert r.json()["status"] == "viewed"

    r = await client.post(f"/api/v1/talents/offers/{offer['id']}/respond", headers=w["cand_h"],
                          json={"decision": "accepted", "note": "  Seshanba qulay  "})
    assert r.json()["status"] == "responded" and r.json()["response_note"] == "Seshanba qulay"
    r = await client.post(f"/api/v1/talents/offers/{offer['id']}/respond", headers=w["cand_h"],
                          json={"decision": "declined"})
    assert r.status_code == 409

    sent = (await client.get("/api/v1/talents/offers/sent", headers=w["alpha_h"])).json()
    assert sent[0]["response"] == "accepted" and sent[0]["candidate_email"] == "cand@test.uz"
    # javob berilgan — yangi taklif yuborish mumkin
    assert (await _offer(client, w, position_title="Middle Backend")).status_code == 201


async def test_decline_and_hide_company(client, db_session, world):
    w = world
    offer = (await _offer(client, w)).json()
    r = await client.post(f"/api/v1/talents/offers/{offer['id']}/respond", headers=w["cand_h"],
                          json={"decision": "accepted", "hide_company": True})
    assert r.status_code == 422
    r = await client.post(f"/api/v1/talents/offers/{offer['id']}/respond", headers=w["cand_h"],
                          json={"decision": "declined", "hide_company": True})
    assert r.json()["response"] == "declined"

    vis = (await client.get("/api/v1/users/me/visibility", headers=w["cand_h"])).json()
    assert vis == {"is_open_to_work": True, "hidden_from_company_ids": [str(w["alpha"].id)]}
    assert _ids(await client.get("/api/v1/talents", headers=w["alpha_h"])) == set()
    sent = (await client.get("/api/v1/talents/offers/sent", headers=w["alpha_h"])).json()
    assert sent[0]["candidate_email"] is None


async def test_cannot_touch_someone_elses_offer(client, db_session, test_user_factory, world):
    offer = (await _offer(client, world)).json()
    _, intruder_h = await _student(client, db_session, test_user_factory, "x@test.uz", "X")
    for path in ("view", "respond"):
        r = await client.post(f"/api/v1/talents/offers/{offer['id']}/{path}", headers=intruder_h,
                              json={"decision": "accepted"})
        assert r.status_code == 404
    row = (await db_session.execute(select(TalentOffer))).scalars().one()
    await db_session.refresh(row)
    assert row.status == TalentOfferStatus.SENT


async def test_offer_validation(client, world):
    assert (await _offer(client, world, message="qisqa")).status_code == 422
    assert (await _offer(client, world, candidate_user_id=str(uuid.uuid4()))).status_code == 404


async def test_inactive_candidate_disappears(client, db_session, world):
    user = await db_session.get(User, world["cand"].id)
    user.is_active = False
    await db_session.commit()
    assert _ids(await client.get("/api/v1/talents", headers=world["alpha_h"])) == set()
    assert (await client.get(f"/api/v1/talents/{user.id}", headers=world["alpha_h"])).status_code == 404
