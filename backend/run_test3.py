import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import Base, engine, AsyncSessionLocal
from app.models.user import User
from app.models.rbac import Role, Permission
from app.core.security import get_password_hash
import uuid

async def run():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with AsyncSessionLocal() as db_session:
        role = Role(id=uuid.uuid4(), name="student")
        db_session.add(role)
        await db_session.commit()
        
        user = User(
            email="student@example.com",
            hashed_password=get_password_hash("pass"),
            full_name="Test User",
            role_id=role.id,
            is_active=True
        )
        db_session.add(user)
        await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/api/v1/auth/login", data={"username": "student@example.com", "password": "pass"})
        token = res.json()["access_token"]
        print("LOGIN:", res.status_code)
        
        res2 = await client.get("/api/v1/talents", headers={"Authorization": f"Bearer {token}"})
        print("TALENTS:", res2.status_code, res2.json())
asyncio.run(run())
