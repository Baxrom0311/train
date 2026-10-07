"""
B2B (kompaniya/universitet) ro'yxatdan o'tish va tasdiqlov oqimini
to'liq sinaydi. Avvalgi versiyada bu oqim butunlay ishlamas edi:
- register-org client'dan tasdiqlanmagan org_id qabul qilardi
- approve_org tashkilotni tasdiqlardi, lekin foydalanuvchini faollashtirmasdi
- login/refresh is_active'ni tekshirmasdi
Shu uchlik sinovdan o'tkazilmagan edi — shuning uchun bu fayl.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.billing import Company, University
from app.models.user import User
from app.models.rbac import Role, Permission


@pytest.fixture
async def admin_token(db_session: AsyncSession, test_user_factory):
    result = await db_session.execute(select(Role).where(Role.name == "admin"))
    admin_role = result.scalars().first()
    perm_result = await db_session.execute(
        select(Permission).where(Permission.key == "approve_companies")
    )
    perm = perm_result.scalars().first()
    if perm not in admin_role.permissions:
        admin_role.permissions.append(perm)
        await db_session.commit()

    admin = await test_user_factory("admin_org@example.com", "pass12345", "admin")
    from app.core.security import create_access_token
    return create_access_token(str(admin.id))


@pytest.mark.asyncio
async def test_register_org_creates_company_unverified(client: AsyncClient, db_session: AsyncSession):
    """register-org o'zi Company yozuvini yaratishi, client'dan mavjud
    org_id so'ramasligi kerak."""
    res = await client.post(
        "/api/v1/auth/register-org",
        json={
            "email": "hr@newcompany.uz",
            "password": "pass12345",
            "full_name": "HR Manager",
            "org_type": "company",
            "org_name": "NorthStack LLC",
            "industry": "IT",
        },
    )
    # ariza qabul qilindi, token yo'q — akkaunt hali yopiq (CONTRACT.md §11.1)
    assert res.status_code == 202
    assert res.json() == {"status": "pending", "org_type": "company", "org_name": "NorthStack LLC"}

    result = await db_session.execute(select(Company).where(Company.name == "NorthStack LLC"))
    company = result.scalars().first()
    assert company is not None
    assert company.is_verified is False

    user_result = await db_session.execute(select(User).where(User.email == "hr@newcompany.uz"))
    user = user_result.scalars().first()
    assert user.is_active is False
    assert user.org_id == company.id


@pytest.mark.asyncio
async def test_inactive_org_user_cannot_login(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register-org",
        json={
            "email": "hr2@pendingco.uz",
            "password": "pass12345",
            "full_name": "HR Two",
            "org_type": "company",
            "org_name": "Pending Co",
            "industry": "Finance",
        },
    )
    res = await client.post(
        "/api/v1/auth/login",
        data={"username": "hr2@pendingco.uz", "password": "pass12345"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_approve_org_activates_pending_users(
    client: AsyncClient, db_session: AsyncSession, admin_token: str
):
    """Tashkilot tasdiqlangach, unga tegishli foydalanuvchi(lar) ham
    avtomatik faollashishi kerak (avvalgi versiyada bu qadam yo'q edi)."""
    await client.post(
        "/api/v1/auth/register-org",
        json={
            "email": "hr3@approveco.uz",
            "password": "pass12345",
            "full_name": "HR Three",
            "org_type": "company",
            "org_name": "Approve Co",
            "industry": "IT",
        },
    )
    result = await db_session.execute(select(Company).where(Company.name == "Approve Co"))
    company = result.scalars().first()

    approve_res = await client.post(
        f"/api/v1/admin/orgs/{company.id}/approve",
        json={"org_type": "company"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert approve_res.status_code == 200

    user_result = await db_session.execute(select(User).where(User.email == "hr3@approveco.uz"))
    user = user_result.scalars().first()
    assert user.is_active is True

    login_res = await client.post(
        "/api/v1/auth/login",
        data={"username": "hr3@approveco.uz", "password": "pass12345"},
    )
    assert login_res.status_code == 200


@pytest.mark.asyncio
async def test_register_org_university_creates_university(client: AsyncClient, db_session: AsyncSession):
    res = await client.post(
        "/api/v1/auth/register-org",
        json={
            "email": "dean@newuni.uz",
            "password": "pass12345",
            "full_name": "Dean Person",
            "org_type": "university",
            "org_name": "New State University",
            "city": "Tashkent",
        },
    )
    assert res.status_code == 202
    result = await db_session.execute(select(University).where(University.name == "New State University"))
    uni = result.scalars().first()
    assert uni is not None
    assert uni.is_verified is False


@pytest.mark.asyncio
async def test_student_register_with_valid_university_id(client: AsyncClient, db_session: AsyncSession):
    uni = University(name="Linked Uni", city="Samarkand", contact_email="x@x.com", is_verified=True)
    db_session.add(uni)
    await db_session.commit()
    await db_session.refresh(uni)

    res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "student_linked@example.com",
            "password": "pass12345",
            "full_name": "Linked Student",
            "university_id": str(uni.id),
        },
    )
    assert res.status_code == 200

    user_result = await db_session.execute(
        select(User).where(User.email == "student_linked@example.com")
    )
    user = user_result.scalars().first()
    assert user.university_id == uni.id


@pytest.mark.asyncio
async def test_student_register_with_unknown_university_id_rejected(client: AsyncClient):
    import uuid
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "student_bad_uni@example.com",
            "password": "pass12345",
            "full_name": "Bad Uni Student",
            "university_id": str(uuid.uuid4()),
        },
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_weak_password_rejected(client: AsyncClient):
    res = await client.post(
        "/api/v1/auth/register",
        json={"email": "weak@example.com", "password": "123", "full_name": "Weak"},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_invalid_email_rejected(client: AsyncClient):
    res = await client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "pass12345", "full_name": "Bad Email"},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_register_org_duplicate_name_rejected(client: AsyncClient):
    body = {"password": "pass12345", "full_name": "HR", "org_type": "company", "industry": "IT"}
    r = await client.post("/api/v1/auth/register-org", json={**body, "email": "a@dup.uz", "org_name": "Dup Labs"})
    assert r.status_code == 202
    r = await client.post("/api/v1/auth/register-org", json={**body, "email": "b@dup.uz", "org_name": "  dup labs "})
    assert r.status_code == 409
