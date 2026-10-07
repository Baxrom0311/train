import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.billing import University
from app.models.user import User
from app.models.rbac import Role, Permission
from app.models.simulation import Submission, Simulation, SimulationTask
from app.core.security import create_access_token

@pytest.fixture
async def setup_university_data(db_session: AsyncSession, test_user_factory):
    result = await db_session.execute(select(Role).where(Role.name == "university_admin"))
    uni_role = result.scalars().first()
    
    perm = Permission(id=uuid.uuid4(), key="manage_universities")
    db_session.add(perm)
    uni_role.permissions.append(perm)
    await db_session.commit()
    
    ver_uni_id = uuid.uuid4()
    unver_uni_id = uuid.uuid4()
    
    ver_uni = University(id=ver_uni_id, name="Ver Uni", city="City", contact_email="v@v.com", is_verified=True)
    unver_uni = University(id=unver_uni_id, name="Unver Uni", city="City", contact_email="u@u.com", is_verified=False)
    
    db_session.add_all([ver_uni, unver_uni])
    await db_session.commit()
    
    ver_admin = await test_user_factory("vadmin@v.com", "pass", "university_admin")
    ver_admin.org_type = "university"
    ver_admin.org_id = ver_uni_id
    
    unver_admin = await test_user_factory("uadmin@u.com", "pass", "university_admin")
    unver_admin.org_type = "university"
    unver_admin.org_id = unver_uni_id
    
    student1 = await test_user_factory("s1@v.com", "pass", "student")
    student1.university_id = ver_uni_id
    student1.full_name = "Student One"
    
    student2 = await test_user_factory("s2@v.com", "pass", "student")
    student2.university_id = ver_uni_id
    student2.full_name = "Student Two"
    
    other_student = await test_user_factory("os@o.com", "pass", "student")
    other_student.university_id = unver_uni_id
    
    sim_id = uuid.uuid4()
    sim = Simulation(
        id=sim_id, title="Sim1", description="desc", sector="IT", difficulty="Easy", company_name="C"
    )
    db_session.add(sim)
    
    task1_id = uuid.uuid4()
    task1 = SimulationTask(
        id=task1_id, simulation_id=sim_id, order_index=1, title="T1", description="desc", expected_skills=["python"]
    )
    db_session.add(task1)
    
    sub1 = Submission(
        task_id=task1_id, user_id=student1.id, content="code1", ai_score=80.0
    )
    sub2 = Submission(
        task_id=task1_id, user_id=student1.id, content="code2", ai_score=90.0
    )
    sub3 = Submission(
        task_id=task1_id, user_id=student2.id, content="code3", ai_score=None
    )
    db_session.add_all([sub1, sub2, sub3])
    
    await db_session.commit()
    
    await db_session.refresh(ver_admin)
    await db_session.refresh(unver_admin)
    await db_session.refresh(student1)
    await db_session.refresh(student2)
    await db_session.refresh(other_student)
    await db_session.refresh(ver_uni)
    await db_session.refresh(unver_uni)
    
    return {
        "ver_admin": ver_admin,
        "unver_admin": unver_admin,
        "student1": student1,
        "student2": student2,
        "other_student": other_student,
        "ver_uni": ver_uni,
        "unver_uni": unver_uni
    }

@pytest.mark.asyncio
async def test_students_list_forbidden(client: AsyncClient, setup_university_data):
    student = setup_university_data["student1"]
    token = create_access_token(str(student.id))
    headers = {"Authorization": f"Bearer {token}"}
    
    response = await client.get("/api/v1/university/students", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Not enough permissions"


@pytest.mark.asyncio
async def test_students_list_unverified_university(client: AsyncClient, setup_university_data):
    admin = setup_university_data["unver_admin"]
    token = create_access_token(str(admin.id))
    headers = {"Authorization": f"Bearer {token}"}
    
    response = await client.get("/api/v1/university/students", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "University not verified yet"


@pytest.mark.asyncio
async def test_students_list_success(client: AsyncClient, setup_university_data):
    admin = setup_university_data["ver_admin"]
    token = create_access_token(str(admin.id))
    headers = {"Authorization": f"Bearer {token}"}
    
    response = await client.get("/api/v1/university/students", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    emails = [s["email"] for s in data]
    assert "s1@v.com" in emails
    assert "s2@v.com" in emails
    assert "os@o.com" not in emails


@pytest.mark.asyncio
async def test_student_progress(client: AsyncClient, setup_university_data):
    admin = setup_university_data["ver_admin"]
    student1 = setup_university_data["student1"]
    other_student = setup_university_data["other_student"]
    
    token = create_access_token(str(admin.id))
    headers = {"Authorization": f"Bearer {token}"}
    
    # Progress for own student
    response = await client.get(f"/api/v1/university/students/{student1.id}/progress", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["student"]["email"] == "s1@v.com"
    assert len(data["submissions"]) == 2
    scores = [s["ai_score"] for s in data["submissions"]]
    assert 80.0 in scores
    assert 90.0 in scores
    
    # Progress for other student (should be 404)
    response = await client.get(f"/api/v1/university/students/{other_student.id}/progress", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_university_stats(client: AsyncClient, setup_university_data):
    admin = setup_university_data["ver_admin"]
    token = create_access_token(str(admin.id))
    headers = {"Authorization": f"Bearer {token}"}
    
    response = await client.get("/api/v1/university/stats", headers=headers)
    assert response.status_code == 200
    data = response.json()
    
    assert data["total_students"] == 2
    assert data["total_submissions"] == 3
    # Two valid scores: 80 and 90. average is 85.0
    assert data["avg_score"] == 85.0
    
    top = data["top_students"]
    assert len(top) == 2
    # Student1: 2 subs, avg 85. Student2: 1 sub, avg 0 (since ai_score=None)
    assert top[0]["full_name"] == "Student One"
    assert top[0]["total_submissions"] == 2
    assert top[0]["avg_score"] == 85.0
    
    assert top[1]["full_name"] == "Student Two"
    assert top[1]["total_submissions"] == 1
    assert top[1]["avg_score"] == 0.0

