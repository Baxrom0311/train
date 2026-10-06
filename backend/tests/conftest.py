import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
import uuid
from sqlalchemy import text

from app.database import Base, get_db
from app.main import app
from app.models.rbac import Role, Permission
from app.models.user import User
from app.core.security import get_password_hash

# Use an in-memory SQLite database for tests
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = async_sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession,
    expire_on_commit=False
)

async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(autouse=True, scope="function")
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Insert roles and permissions
    async with TestingSessionLocal() as session:
        student_role = Role(id=uuid.uuid4(), name="student")
        hr_role = Role(id=uuid.uuid4(), name="company_hr")
        uni_role = Role(id=uuid.uuid4(), name="university_admin")
        admin_role = Role(id=uuid.uuid4(), name="admin")
        
        manage_billing = Permission(id=uuid.uuid4(), key="manage_billing")
        approve_companies = Permission(id=uuid.uuid4(), key="approve_companies")
        
        session.add_all([student_role, hr_role, uni_role, admin_role])
        session.add_all([manage_billing, approve_companies])
        
        admin_role.permissions.extend([manage_billing, approve_companies])
        
        await session.commit()
        
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session

@pytest.fixture
async def test_user_factory(db_session: AsyncSession):
    async def _create_test_user(email: str, password: str, role_name: str = "student", is_active: bool = True):
        from sqlalchemy.future import select
        result = await db_session.execute(select(Role).where(Role.name == role_name))
        role = result.scalars().first()
        user = User(
            email=email,
            hashed_password=get_password_hash(password),
            full_name="Test User",
            role_id=role.id,
            is_active=is_active
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user
    return _create_test_user
