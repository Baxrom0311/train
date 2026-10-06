import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.billing import Company
from app.models.user import CandidateVisibility
from app.models.talent import TalentOffer
from app.models.rbac import Role, Permission
import uuid
from app.models.simulation import Submission

@pytest.fixture(autouse=True)
def disable_expire_on_commit(db_session: AsyncSession):
    db_session.sync_session.expire_on_commit = False

@pytest.fixture
async def verified_company(db_session: AsyncSession):
    company = Company(
        id=uuid.uuid4(),
        name="Verified Corp",
        industry="Tech",
        contact_email="hr@verified.com",
        is_verified=True,
    )
    db_session.add(company)
    await db_session.commit()
    return company

@pytest.fixture
async def unverified_company(db_session: AsyncSession):
    company = Company(
        id=uuid.uuid4(),
        name="Unverified Corp",
        industry="Tech",
        contact_email="hr@unverified.com",
        is_verified=False,
    )
    db_session.add(company)
    await db_session.commit()
    return company

@pytest.fixture
async def add_hr_permissions(db_session: AsyncSession):
    result = await db_session.execute(select(Role).where(Role.name == "company_hr"))
    hr_role = result.scalars().first()
    view_candidates = Permission(id=uuid.uuid4(), key="view_candidates")
    db_session.add(view_candidates)
    hr_role.permissions.append(view_candidates)
    await db_session.commit()

@pytest.fixture
async def open_candidate(db_session: AsyncSession, test_user_factory):
    user = await test_user_factory("open@example.com", "pass", "student")
    visibility = CandidateVisibility(
        user_id=user.id,
        is_open_to_work=True,
        hidden_from_company_ids=[]
    )
    db_session.add(visibility)
    await db_session.commit()
    return user

@pytest.fixture
async def hidden_candidate(db_session: AsyncSession, test_user_factory, verified_company):
    user = await test_user_factory("hidden@example.com", "pass", "student")
    visibility = CandidateVisibility(
        user_id=user.id,
        is_open_to_work=True,
        hidden_from_company_ids=[str(verified_company.id)]
    )
    db_session.add(visibility)
    await db_session.commit()
    return user

@pytest.mark.asyncio
async def test_talent_list_forbidden_student(client: AsyncClient, test_user_factory, add_hr_permissions):
    user = await test_user_factory("student@example.com", "pass", "student")
    response = await client.post("/api/v1/auth/login", data={"username": "student@example.com", "password": "pass"})
    token = response.json()["access_token"]
    
    res = await client.get("/api/v1/talents", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403

@pytest.mark.asyncio
async def test_talent_list_unverified_company(client: AsyncClient, test_user_factory, unverified_company, db_session: AsyncSession, add_hr_permissions):
    user = await test_user_factory("hr2@example.com", "pass", "company_hr")
    user.org_type = "company"
    user.org_id = unverified_company.id
    db_session.add(user)
    await db_session.commit()
    
    response = await client.post("/api/v1/auth/login", data={"username": "hr2@example.com", "password": "pass"})
    token = response.json()["access_token"]
    
    res = await client.get("/api/v1/talents", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403

@pytest.mark.asyncio
async def test_talent_list_success(client: AsyncClient, test_user_factory, verified_company, open_candidate, db_session: AsyncSession, add_hr_permissions):
    user = await test_user_factory("hr@example.com", "pass", "company_hr")
    user.org_type = "company"
    user.org_id = verified_company.id
    db_session.add(user)
    await db_session.commit()
    
    response = await client.post("/api/v1/auth/login", data={"username": "hr@example.com", "password": "pass"})
    token = response.json()["access_token"]
    
    res = await client.get("/api/v1/talents", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert any(c["id"] == str(open_candidate.id) for c in data)

@pytest.mark.asyncio
async def test_hidden_candidate(client: AsyncClient, test_user_factory, verified_company, hidden_candidate, db_session: AsyncSession, add_hr_permissions):
    user = await test_user_factory("hr_hidden@example.com", "pass", "company_hr")
    user.org_type = "company"
    user.org_id = verified_company.id
    db_session.add(user)
    await db_session.commit()
    
    response = await client.post("/api/v1/auth/login", data={"username": "hr_hidden@example.com", "password": "pass"})
    token = response.json()["access_token"]
    
    res = await client.get("/api/v1/talents", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert not any(c["id"] == str(hidden_candidate.id) for c in data)

@pytest.mark.asyncio
async def test_send_offer(client: AsyncClient, test_user_factory, verified_company, open_candidate, db_session: AsyncSession, add_hr_permissions):
    user = await test_user_factory("hr_offer@example.com", "pass", "company_hr")
    user.org_type = "company"
    user.org_id = verified_company.id
    db_session.add(user)
    await db_session.commit()
    
    response = await client.post("/api/v1/auth/login", data={"username": "hr_offer@example.com", "password": "pass"})
    token = response.json()["access_token"]
    
    offer_data = {
        "candidate_id": str(open_candidate.id),
        "message": "We want to hire you!"
    }
    res = await client.post("/api/v1/talents/offers", json=offer_data, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["message"] == "We want to hire you!"
    assert data["company_id"] == str(verified_company.id)
    assert data["candidate_id"] == str(open_candidate.id)
