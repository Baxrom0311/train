import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.rbac import Permission, Role
from app.models.billing import Company
from app.models.case_cup import CaseCup
import uuid
from datetime import datetime, timedelta, timezone

@pytest.fixture
async def setup_case_cup_permissions(db_session: AsyncSession):
    # Instead of creating, we might just query or create if not exists
    result = await db_session.execute(select(Permission).where(Permission.key == "manage_simulations"))
    manage_sims = result.scalars().first()
    if not manage_sims:
        manage_sims = Permission(id=uuid.uuid4(), key="manage_simulations")
        db_session.add(manage_sims)
        
    result = await db_session.execute(select(Role).where(Role.name == "admin"))
    admin_role = result.scalars().first()
    if admin_role and manage_sims not in admin_role.permissions:
        admin_role.permissions.append(manage_sims)
    await db_session.commit()

@pytest.fixture
async def test_company(db_session: AsyncSession):
    company = Company(
        id=uuid.uuid4(),
        name=f"Atlas Global Finance {uuid.uuid4()}",
        industry="Banking",
        contact_email="contact@atlas.com",
        is_verified=True
    )
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)
    db_session.expunge(company)
    return company

@pytest.mark.asyncio
async def test_create_case_cup_forbidden(client: AsyncClient, test_user_factory, test_company):
    user = await test_user_factory(f"student_{uuid.uuid4()}@example.com", "pass", "student")
    response = await client.post("/api/v1/auth/login", data={"username": user.email, "password": "pass"})
    token = response.json()["access_token"]
    
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {
        "title": "Fintech Case Cup",
        "description": "Solve fintech problems",
        "company_id": str(test_company.id),
        "sector": "Banking",
        "start_date": datetime.now(timezone.utc).isoformat(),
        "end_date": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "is_active": True
    }
    
    res = await client.post("/api/v1/case-cups", json=payload, headers=headers)
    assert res.status_code == 403

@pytest.mark.asyncio
async def test_create_case_cup_admin(client: AsyncClient, test_user_factory, test_company, setup_case_cup_permissions):
    admin = await test_user_factory(f"admin_{uuid.uuid4()}@example.com", "pass", "admin")
    response = await client.post("/api/v1/auth/login", data={"username": admin.email, "password": "pass"})
    token = response.json()["access_token"]
    
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {
        "title": "Fintech Case Cup",
        "description": "Solve fintech problems",
        "company_id": str(test_company.id),
        "sector": "Banking",
        "start_date": datetime.now(timezone.utc).isoformat(),
        "end_date": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "is_active": True
    }
    
    res = await client.post("/api/v1/case-cups", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == payload["title"]
    assert "id" in data

@pytest.mark.asyncio
async def test_list_case_cups(client: AsyncClient, test_user_factory, test_company, setup_case_cup_permissions):
    admin = await test_user_factory(f"admin_{uuid.uuid4()}@example.com", "pass", "admin")
    response = await client.post("/api/v1/auth/login", data={"username": admin.email, "password": "pass"})
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {
        "title": "List Case Cup",
        "description": "List desc",
        "company_id": str(test_company.id),
        "sector": "IT",
        "start_date": datetime.now(timezone.utc).isoformat(),
        "end_date": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "is_active": True
    }
    create_res = await client.post("/api/v1/case-cups", json=payload, headers=headers)
    assert create_res.status_code == 201
    
    user = await test_user_factory(f"student_{uuid.uuid4()}@example.com", "pass", "student")
    user_res = await client.post("/api/v1/auth/login", data={"username": user.email, "password": "pass"})
    user_token = user_res.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}
    
    list_res = await client.get("/api/v1/case-cups", headers=user_headers)
    assert list_res.status_code == 200
    data = list_res.json()
    assert len(data) >= 1
    assert any(c["title"] == "List Case Cup" for c in data)

@pytest.mark.asyncio
async def test_submit_case_cup(client: AsyncClient, test_user_factory, test_company, setup_case_cup_permissions):
    admin = await test_user_factory(f"admin_{uuid.uuid4()}@example.com", "pass", "admin")
    response = await client.post("/api/v1/auth/login", data={"username": admin.email, "password": "pass"})
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {
        "title": "Submit Case Cup",
        "description": "Submit desc",
        "company_id": str(test_company.id),
        "sector": "IT",
        "start_date": datetime.now(timezone.utc).isoformat(),
        "end_date": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "is_active": True
    }
    create_res = await client.post("/api/v1/case-cups", json=payload, headers=headers)
    cup_id = create_res.json()["id"]
    
    user = await test_user_factory(f"student_{uuid.uuid4()}@example.com", "pass", "student")
    user_res = await client.post("/api/v1/auth/login", data={"username": user.email, "password": "pass"})
    user_token = user_res.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}
    
    submit_payload = {"content": "This is a great business solution for the case cup."}
    submit_res = await client.post(f"/api/v1/case-cups/{cup_id}/submit", json=submit_payload, headers=user_headers)
    assert submit_res.status_code == 201
    submit_data = submit_res.json()
    assert submit_data["ai_score"] is not None
    assert 60 <= submit_data["ai_score"] <= 100

@pytest.mark.asyncio
async def test_leaderboard(client: AsyncClient, test_user_factory, test_company, setup_case_cup_permissions):
    admin = await test_user_factory(f"admin_{uuid.uuid4()}@example.com", "pass", "admin")
    response = await client.post("/api/v1/auth/login", data={"username": admin.email, "password": "pass"})
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {
        "title": "Leaderboard Case Cup",
        "description": "Desc",
        "company_id": str(test_company.id),
        "sector": "IT",
        "start_date": datetime.now(timezone.utc).isoformat(),
        "end_date": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "is_active": True
    }
    create_res = await client.post("/api/v1/case-cups", json=payload, headers=headers)
    cup_id = create_res.json()["id"]
    
    u1 = await test_user_factory(f"student_lb_1_{uuid.uuid4()}@example.com", "pass", "student")
    u1_res = await client.post("/api/v1/auth/login", data={"username": u1.email, "password": "pass"})
    h1 = {"Authorization": f"Bearer {u1_res.json()['access_token']}"}
    await client.post(f"/api/v1/case-cups/{cup_id}/submit", json={"content": "Answer 1"}, headers=h1)
    
    u2 = await test_user_factory(f"student_lb_2_{uuid.uuid4()}@example.com", "pass", "student")
    u2_res = await client.post("/api/v1/auth/login", data={"username": u2.email, "password": "pass"})
    h2 = {"Authorization": f"Bearer {u2_res.json()['access_token']}"}
    await client.post(f"/api/v1/case-cups/{cup_id}/submit", json={"content": "Answer 2"}, headers=h2)
    
    lb_res = await client.get(f"/api/v1/case-cups/{cup_id}/leaderboard", headers=h1)
    assert lb_res.status_code == 200
    lb_data = lb_res.json()
    assert len(lb_data) == 2
    
    assert lb_data[0]["ai_score"] >= lb_data[1]["ai_score"]
    assert lb_data[0]["rank"] == 1
    assert lb_data[1]["rank"] == 2
