"""
test_talent_visibility.py — CandidateVisibility default-yopiq (opt-in) testlari.

Qabul qilish mezonlari (docs/tasks/04-talent-hunt.md §3):
  1. Yangi student /talents da ko'rinmaydi (CandidateVisibility yozuvi yo'q).
  2. is_open_to_work=True qilgandan keyin ko'rinadi.
  3. hidden_from_company_ids ga qo'yilgan company uchun ko'rinmaydi,
     boshqa company uchun ko'rinadi.
"""
import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.billing import Company
from app.models.talent import CandidateVisibility
from app.models.rbac import Role, Permission


# ---------------------------------------------------------------------------
# Fixture: tasdiqlangan kompaniya + view_candidates ruxsati
# ---------------------------------------------------------------------------

@pytest.fixture
async def verified_company_a(db_session: AsyncSession) -> Company:
    company = Company(
        id=uuid.uuid4(),
        name="Alpha Corp",
        industry="Tech",
        contact_email="hr@alpha.com",
        is_verified=True,
    )
    db_session.add(company)
    await db_session.commit()
    return company


@pytest.fixture
async def verified_company_b(db_session: AsyncSession) -> Company:
    company = Company(
        id=uuid.uuid4(),
        name="Beta Corp",
        industry="Finance",
        contact_email="hr@beta.com",
        is_verified=True,
    )
    db_session.add(company)
    await db_session.commit()
    return company


@pytest.fixture
async def setup_hr_permission(db_session: AsyncSession):
    """company_hr roliga view_candidates ruxsatini beradi."""
    result = await db_session.execute(select(Role).where(Role.name == "company_hr"))
    hr_role = result.scalars().first()
    view_perm = Permission(id=uuid.uuid4(), key="view_candidates")
    db_session.add(view_perm)
    hr_role.permissions.append(view_perm)
    await db_session.commit()


async def _login(client: AsyncClient, email: str, password: str) -> str:
    """Login qilib access token qaytaradi."""
    resp = await client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


async def _make_hr_user(test_user_factory, db_session, company_id):
    """company_hr rolida kompaniyaga bog'liq user yaratadi."""
    user = await test_user_factory(f"hr_{uuid.uuid4().hex[:6]}@test.com", "pass", "company_hr")
    user.org_type = "company"
    user.org_id = company_id
    db_session.add(user)
    await db_session.commit()
    return user


# ---------------------------------------------------------------------------
# TEST 1: Yangi student (CandidateVisibility yo'q) /talents da ko'rinmaydi
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_new_student_not_visible_by_default(
    client: AsyncClient,
    test_user_factory,
    db_session: AsyncSession,
    verified_company_a: Company,
    setup_hr_permission,
):
    """
    CandidateVisibility yozuvi umuman yo'q bo'lsa — student /talents da
    chiqmasligi shart. Bu ENG MUHIM test (CONTRACT.md §5, 04-talent-hunt.md §3).
    """
    # 1. Yangi student — CandidateVisibility yozuvi yaratilmaydi
    student = await test_user_factory("new_student@test.com", "pass", "student")

    # 2. Hech qanday CandidateVisibility yozuvi yo'qligini tasdiqlash
    result = await db_session.execute(
        select(CandidateVisibility).where(CandidateVisibility.user_id == student.id)
    )
    assert result.scalars().first() is None, "Yangi student uchun CandidateVisibility bo'lmasligi kerak"

    # 3. HR sifatida login qilib /talents so'rov yuboramiz
    hr_user = await _make_hr_user(test_user_factory, db_session, verified_company_a.id)
    token = await _login(client, hr_user.email, "pass")

    resp = await client.get("/api/v1/talents", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()]
    assert str(student.id) not in ids, (
        "Yangi student (CandidateVisibility yo'q) /talents da chiqmasligi kerak"
    )


# ---------------------------------------------------------------------------
# TEST 2: is_open_to_work=True qilgandan keyin student ko'rinadi
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_student_visible_after_opt_in(
    client: AsyncClient,
    test_user_factory,
    db_session: AsyncSession,
    verified_company_a: Company,
    setup_hr_permission,
):
    """
    PATCH /users/me/visibility {is_open_to_work: true} dan keyin
    /talents da ko'rinishi kerak.
    """
    student = await test_user_factory("opt_in@test.com", "pass", "student")
    student_token = await _login(client, "opt_in@test.com", "pass")

    # Student o'zi ko'rinishni yoqadi
    patch_resp = await client.patch(
        "/api/v1/users/me/visibility",
        json={"is_open_to_work": True, "hidden_from_company_ids": []},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["is_open_to_work"] is True

    # HR sifatida /talents da ko'rinishini tekshiramiz
    hr_user = await _make_hr_user(test_user_factory, db_session, verified_company_a.id)
    hr_token = await _login(client, hr_user.email, "pass")

    resp = await client.get("/api/v1/talents", headers={"Authorization": f"Bearer {hr_token}"})
    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()]
    assert str(student.id) in ids, "is_open_to_work=True dan keyin /talents da ko'rinishi kerak"


# ---------------------------------------------------------------------------
# TEST 3: hidden_from_company_ids ga qo'yilgan company uchun ko'rinmaydi
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_student_hidden_from_specific_company(
    client: AsyncClient,
    test_user_factory,
    db_session: AsyncSession,
    verified_company_a: Company,
    verified_company_b: Company,
    setup_hr_permission,
):
    """
    hidden_from_company_ids = [company_a.id] bo'lsa:
      - company_a GET /talents da student ko'rinmaydi
      - company_b GET /talents da student ko'rinadi
    """
    student = await test_user_factory("hidden_test@test.com", "pass", "student")
    student_token = await _login(client, "hidden_test@test.com", "pass")

    # Student company_a dan yashirinadi, lekin umumiy open_to_work=True
    patch_resp = await client.patch(
        "/api/v1/users/me/visibility",
        json={
            "is_open_to_work": True,
            "hidden_from_company_ids": [str(verified_company_a.id)],
        },
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert patch_resp.status_code == 200

    # Company A HR — ko'rinmasligi kerak
    hr_a = await _make_hr_user(test_user_factory, db_session, verified_company_a.id)
    token_a = await _login(client, hr_a.email, "pass")
    resp_a = await client.get("/api/v1/talents", headers={"Authorization": f"Bearer {token_a}"})
    assert resp_a.status_code == 200
    ids_a = [c["id"] for c in resp_a.json()]
    assert str(student.id) not in ids_a, (
        "Company A uchun yashirilgan student company A /talents da chiqmasligi kerak"
    )

    # Company B HR — ko'rinishi kerak
    hr_b = await _make_hr_user(test_user_factory, db_session, verified_company_b.id)
    token_b = await _login(client, hr_b.email, "pass")
    resp_b = await client.get("/api/v1/talents", headers={"Authorization": f"Bearer {token_b}"})
    assert resp_b.status_code == 200
    ids_b = [c["id"] for c in resp_b.json()]
    assert str(student.id) in ids_b, (
        "Company B uchun yashirilmagan student company B /talents da ko'rinishi kerak"
    )
