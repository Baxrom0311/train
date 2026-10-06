import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.rbac import Permission, Role
import uuid

@pytest.fixture
async def setup_simulation_permissions(db_session: AsyncSession):
    manage_sims = Permission(id=uuid.uuid4(), key="manage_simulations")
    db_session.add(manage_sims)
    result = await db_session.execute(select(Role).where(Role.name == "admin"))
    admin_role = result.scalars().first()
    if admin_role:
        admin_role.permissions.append(manage_sims)
    await db_session.commit()

@pytest.mark.asyncio
async def test_create_simulation_forbidden(client: AsyncClient, test_user_factory, setup_simulation_permissions):
    user = await test_user_factory("student_f@example.com", "pass", "student")
    response = await client.post("/api/v1/auth/login", data={"username": "student_f@example.com", "password": "pass"})
    token = response.json()["access_token"]
    
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {
        "title": "Test Sim",
        "description": "Desc",
        "sector": "IT",
        "difficulty": "beginner",
        "company_name": "Elon Market",
        "tasks": [{"title": "Task 1", "description": "Do this", "expected_skills": ["Python"]}]
    }
    res = await client.post("/api/v1/simulations", json=payload, headers=headers)
    assert res.status_code == 403

@pytest.mark.asyncio
async def test_create_simulation_admin(client: AsyncClient, test_user_factory, setup_simulation_permissions):
    user = await test_user_factory("admin_c@example.com", "pass", "admin")
    response = await client.post("/api/v1/auth/login", data={"username": "admin_c@example.com", "password": "pass"})
    token = response.json()["access_token"]
    
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {
        "title": "Test Sim Admin",
        "description": "Desc",
        "sector": "IT",
        "difficulty": "beginner",
        "company_name": "Elon Market",
        "tasks": [{"title": "Task 1", "description": "Do this", "expected_skills": ["Python"]}]
    }
    res = await client.post("/api/v1/simulations", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Test Sim Admin"

@pytest.mark.asyncio
async def test_list_simulations(client: AsyncClient, test_user_factory, setup_simulation_permissions):
    user = await test_user_factory("admin_l@example.com", "pass", "admin")
    response = await client.post("/api/v1/auth/login", data={"username": "admin_l@example.com", "password": "pass"})
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {
        "title": "Sim 1",
        "description": "Desc",
        "sector": "IT",
        "difficulty": "beginner",
        "company_name": "Atlas Global Finance",
        "tasks": []
    }
    await client.post("/api/v1/simulations", json=payload, headers=headers)
    
    res = await client.get("/api/v1/simulations", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) >= 1

@pytest.mark.asyncio
async def test_submit_and_eval(client: AsyncClient, test_user_factory, setup_simulation_permissions):
    admin = await test_user_factory("admin_s@example.com", "pass", "admin")
    response = await client.post("/api/v1/auth/login", data={"username": "admin_s@example.com", "password": "pass"})
    admin_token = response.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    payload = {
        "title": "Eval Sim",
        "description": "Desc",
        "sector": "IT",
        "difficulty": "beginner",
        "company_name": "NorthBank UZ",
        "tasks": [{"title": "Task", "description": "D", "expected_skills": ["S"]}]
    }
    sim_res = await client.post("/api/v1/simulations", json=payload, headers=admin_headers)
    task_id = sim_res.json()["tasks"][0]["id"]
    
    student = await test_user_factory("student_s@example.com", "pass", "student")
    response = await client.post("/api/v1/auth/login", data={"username": "student_s@example.com", "password": "pass"})
    student_token = response.json()["access_token"]
    student_headers = {"Authorization": f"Bearer {student_token}"}
    
    sub_payload = {"task_id": task_id, "content": "This is my valid submission that passes guardrail"}
    sub_res = await client.post("/api/v1/submissions", json=sub_payload, headers=student_headers)
    
    assert sub_res.status_code == 201
    data = sub_res.json()
    assert data["ai_eval_status"] == "completed"
    assert data["ai_score"] is not None
