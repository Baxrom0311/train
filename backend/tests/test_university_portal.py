"""
Universitet portali (CONTRACT.md §12): talabalar Run natijalari, bog'lanish.

Eng muhim qoidalar: faqat tasdiqlangan universitet xodimi, faqat o'z
talabalari (boshqasi — 404), javob/chat ko'rinmaydi, kompaniya xodimi
"talaba" sifatida chiqmaydi.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models.billing import Company, University
from app.models.enums import RunStatus, ScenarioVersionStatus, Sector
from app.models.scenario import Run, Scenario, ScenarioVersion
from app.models.user import User

pytestmark = pytest.mark.asyncio

NOW = datetime.now(timezone.utc)


async def _headers(client, email):
    r = await client.post("/api/v1/auth/login", data={"username": email, "password": "pass"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _university(db, name, verified=True):
    uni = University(name=name, city="Toshkent", contact_email=f"info@{name.lower()}.uz", is_verified=verified)
    db.add(uni)
    await db.commit()
    return uni


async def _staff(client, db, factory, uni, email):
    user = await factory(email, "pass", "university_admin")
    user.org_type, user.org_id = "university", uni.id
    await db.commit()
    return await _headers(client, email)


async def _student(db, factory, email, name, uni):
    user = await factory(email, "pass", "student")
    user.full_name = name
    user.university_id = uni.id if uni else None
    await db.commit()
    return user


async def _scenario(db, slug, sector=Sector.IT):
    scenario = Scenario(
        slug=slug, title=f"{slug} title", sector=sector, company_name="Lazurit Go",
        difficulty="junior", duration_days=1,
    )
    version = ScenarioVersion(scenario=scenario, version=1, status=ScenarioVersionStatus.PUBLISHED, definition={})
    db.add_all([scenario, version])
    await db.commit()
    return version


async def _run(db, user, version, *, score=None, competencies=None, status=RunStatus.COMPLETED, days_ago=1):
    at = NOW - timedelta(days=days_ago)
    done = status == RunStatus.COMPLETED
    db.add(Run(
        user_id=user.id, scenario_version_id=version.id, status=status,
        start_at=at - timedelta(hours=8), ends_at=at if done else NOW + timedelta(days=1), last_activity_at=at,
        competency_scores=competencies if done else None,
        final_report={
            "overall_score": score, "certificate": True,
            "summary": {"summary": "Yaxshi", "strengths": ["Aniq yozadi"], "improvements": []},
        } if done else None,
    ))
    await db.commit()


@pytest.fixture(autouse=True)
def _no_expire(db_session):
    db_session.sync_session.expire_on_commit = False


@pytest.fixture
async def world(client, db_session, test_user_factory):
    """Bitta universitet: ikki natijali talaba, bitta yangi talaba; begona universitet talabasi."""
    uni = await _university(db_session, "Samdu")
    other = await _university(db_session, "Tatu")
    it = await _scenario(db_session, "it-day1")
    bank = await _scenario(db_session, "bank-day1", Sector.BANKING)

    aziza = await _student(db_session, test_user_factory, "aziza@samdu.uz", "Aziza Rahimova", uni)
    await _run(db_session, aziza, it, score=70.0, competencies={"technical": 60.0}, days_ago=3)
    await _run(db_session, aziza, it, score=90.0, competencies={"technical": 95.0, "communication": 80.0})
    await _run(db_session, aziza, bank, status=RunStatus.ACTIVE)

    bobur = await _student(db_session, test_user_factory, "bobur@samdu.uz", "Bobur Aliyev", uni)
    await _run(db_session, bobur, bank, score=60.0, competencies={"technical": 55.0}, days_ago=2)

    new = await _student(db_session, test_user_factory, "yangi@samdu.uz", "Yangi Talaba", uni)
    stranger = await _student(db_session, test_user_factory, "begona@tatu.uz", "Begona", other)
    await _run(db_session, stranger, it, score=99.0, competencies={"technical": 99.0})

    staff = await _staff(client, db_session, test_user_factory, uni, "dekan@samdu.uz")
    return {"uni": uni, "other": other, "aziza": aziza, "bobur": bobur, "new": new,
            "stranger": stranger, "staff": staff}


# ── Kirish ───────────────────────────────────────────────────────────


async def test_portal_requires_verified_university_staff(client, db_session, test_user_factory, world):
    pending = await _university(db_session, "Pending", verified=False)
    pending_staff = await _staff(client, db_session, test_user_factory, pending, "dekan@pending.uz")
    student = await _headers(client, "aziza@samdu.uz")

    hr = await test_user_factory("hr@kumush.uz", "pass", "company_hr")
    company = Company(name="Kumush", industry="Fintech", contact_email="hr@kumush.uz", is_verified=True)
    db_session.add(company)
    await db_session.commit()
    hr.org_type, hr.org_id = "company", company.id
    await db_session.commit()
    hr_h = await _headers(client, "hr@kumush.uz")

    for h in (pending_staff, student, hr_h):
        assert (await client.get("/api/v1/university/overview", headers=h)).status_code == 403
        assert (await client.get("/api/v1/university/students", headers=h)).status_code == 403
    assert (await client.get("/api/v1/university/students")).status_code == 401


async def test_public_list_shows_only_verified(client, db_session, world):
    await _university(db_session, "Pending", verified=False)
    names = [u["name"] for u in (await client.get("/api/v1/university/list")).json()]
    assert names == ["Samdu", "Tatu"]


# ── Ko'rinish ────────────────────────────────────────────────────────


async def test_overview(client, world):
    data = (await client.get("/api/v1/university/overview", headers=world["staff"])).json()
    assert data["university"]["name"] == "Samdu"
    assert (data["students_total"], data["students_with_results"]) == (3, 2)
    # Aziza: IT'ning eng yaxshi urinishi (90); Bobur: bank (60)
    assert (data["runs_completed"], data["runs_in_progress"]) == (2, 1)
    assert data["avg_score"] == 75.0
    assert data["sectors"] == [
        {"sector": "Banking", "students": 1, "avg_score": 60.0},
        {"sector": "IT", "students": 1, "avg_score": 90.0},
    ]
    assert data["competencies"] == {"communication": 80.0, "technical": 75.0}
    assert [s["full_name"] for s in data["top_students"]] == ["Aziza Rahimova", "Bobur Aliyev"]


async def test_overview_without_students(client, db_session, test_user_factory):
    uni = await _university(db_session, "Bo'sh")
    staff = await _staff(client, db_session, test_user_factory, uni, "dekan@bosh.uz")
    data = (await client.get("/api/v1/university/overview", headers=staff)).json()
    assert data["students_total"] == 0 and data["avg_score"] is None
    assert data["sectors"] == [] and data["competencies"] == {} and data["top_students"] == []


async def test_students_list_filters_and_sorting(client, world):
    get = lambda qs="": client.get(f"/api/v1/university/students{qs}", headers=world["staff"])  # noqa: E731

    data = (await get()).json()
    assert data["total"] == 3
    assert [s["full_name"] for s in data["items"]] == ["Aziza Rahimova", "Bobur Aliyev", "Yangi Talaba"]
    aziza = data["items"][0]
    assert aziza["email"] == "aziza@samdu.uz" and aziza["overall_score"] == 90.0
    assert (aziza["runs_completed"], aziza["runs_in_progress"]) == (1, 1)
    assert data["items"][2]["overall_score"] is None and data["items"][2]["runs_completed"] == 0

    assert [s["full_name"] for s in (await get("?sort=name")).json()["items"]] == [
        "Aziza Rahimova", "Bobur Aliyev", "Yangi Talaba"]
    assert [s["full_name"] for s in (await get("?sort=recent")).json()["items"]] == [
        "Aziza Rahimova", "Bobur Aliyev", "Yangi Talaba"]
    assert [s["full_name"] for s in (await get("?sector=Banking")).json()["items"]] == ["Bobur Aliyev"]
    assert [s["full_name"] for s in (await get("?has_results=false")).json()["items"]] == ["Yangi Talaba"]
    assert [s["full_name"] for s in (await get("?q=BOBUR")).json()["items"]] == ["Bobur Aliyev"]
    assert [s["full_name"] for s in (await get("?q=samdu.uz&limit=1&offset=1")).json()["items"]] == ["Bobur Aliyev"]


async def test_org_staff_is_not_a_student(client, db_session, test_user_factory, world):
    # Tashkilot xodimi university_id bilan ham talaba sifatida chiqmaydi
    colleague = await test_user_factory("kotib@samdu.uz", "pass", "university_admin")
    colleague.org_type, colleague.org_id, colleague.university_id = "university", world["uni"].id, world["uni"].id
    await db_session.commit()
    assert (await client.get("/api/v1/university/students", headers=world["staff"])).json()["total"] == 3


async def test_student_detail(client, world):
    r = await client.get(f"/api/v1/university/students/{world['aziza'].id}", headers=world["staff"])
    assert r.status_code == 200
    data = r.json()
    assert data["competencies"] == {"communication": 80.0, "technical": 95.0}
    [run] = data["runs"]
    assert run["scenario_title"] == "it-day1 title" and run["strengths"] == ["Aniq yozadi"]
    assert [(p["scenario_title"], p["status"]) for p in data["in_progress"]] == [("bank-day1 title", "active")]
    # javoblar, chat, hisobot matni yo'q
    assert not {"final_report", "messages", "answers", "files"} & set(data) and set(run) == {
        "scenario_title", "company_name", "sector", "completed_at", "overall_score", "competency_scores", "strengths"}


async def test_other_university_student_is_not_found(client, world):
    for sid in (world["stranger"].id, uuid.uuid4()):
        assert (await client.get(f"/api/v1/university/students/{sid}", headers=world["staff"])).status_code == 404
        assert (await client.delete(f"/api/v1/university/students/{sid}", headers=world["staff"])).status_code == 404


async def test_detach_student(client, db_session, world):
    r = await client.delete(f"/api/v1/university/students/{world['bobur'].id}", headers=world["staff"])
    assert r.status_code == 204
    await db_session.refresh(world["bobur"])
    assert world["bobur"].university_id is None and await db_session.get(User, world["bobur"].id)
    assert (await client.get("/api/v1/university/students", headers=world["staff"])).json()["total"] == 2


# ── Talaba: o'z universiteti ─────────────────────────────────────────


async def test_student_changes_university(client, db_session, test_user_factory, world):
    h = await _headers(client, "yangi@samdu.uz")
    assert (await client.get("/api/v1/users/me/university", headers=h)).json()["university"]["name"] == "Samdu"

    r = await client.patch("/api/v1/users/me/university", headers=h, json={"university_id": str(world["other"].id)})
    assert r.status_code == 200 and r.json()["university"]["name"] == "Tatu"

    pending = await _university(db_session, "Pending", verified=False)
    for bad in (pending.id, uuid.uuid4()):
        r = await client.patch("/api/v1/users/me/university", headers=h, json={"university_id": str(bad)})
        assert r.status_code == 404

    r = await client.patch("/api/v1/users/me/university", headers=h, json={"university_id": None})
    assert r.json() == {"university": None}
    assert (await client.get("/api/v1/university/students", headers=world["staff"])).json()["total"] == 2


async def test_affiliation_is_student_only(client, world):
    assert (await client.get("/api/v1/users/me/university", headers=world["staff"])).status_code == 403
    r = await client.patch("/api/v1/users/me/university", headers=world["staff"], json={"university_id": None})
    assert r.status_code == 403
