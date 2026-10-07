"""
conftest.py — PostgreSQL test konfiguratsiyasi (CONTRACT.md §3.1).
SQLite ISHLATILMAYDI. Real PostgreSQL tryjob_test database.
NullPool — har connection mustaqil, pool caching yo'q.
asyncio_default_fixture_loop_scope = session — bir event loop.
"""
import os
import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from sqlalchemy import text
import uuid

from app.database import Base, get_db
from app.main import app
from app.models.rbac import Role, Permission
from app.models.user import User
from app.core.security import get_password_hash

# Haqiqiy PostgreSQL test database — SQLite ISHLATILMAYDI (CONTRACT.md §3.1)
_default_test_url = "postgresql+asyncpg://postgres@localhost/tryjob_test"
SQLALCHEMY_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", _default_test_url)

# NullPool — har connection pool caching qilmaydi
engine = create_async_engine(SQLALCHEMY_DATABASE_URL, poolclass=NullPool, echo=False)
TestingSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
async def create_tables():
    """Session boshida bir marta jadvallarni yaratadi."""
    async with engine.begin() as conn:
        # §9.7: document_chunks.embedding — pgvector `vector` tipi
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Session oxirida tozalash
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(autouse=True, scope="function")
async def setup_db(create_tables):
    """
    Har test funksiyasidan oldin barcha ma'lumotlarni tozalab,
    boshlang'ich rollar va ruxsatlarni qayta seed qiladi.
    """
    # Barcha jadvallarni tozalash (FK tartibida)
    async with engine.begin() as conn:
        await conn.execute(text("SET session_replication_role = 'replica'"))
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())
        await conn.execute(text("SET session_replication_role = 'origin'"))

    # Boshlang'ich rollar va ruxsatlarni seed qilish
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
    async def _create_test_user(
        email: str, password: str, role_name: str = "student", is_active: bool = True
    ):
        from sqlalchemy.future import select
        result = await db_session.execute(select(Role).where(Role.name == role_name))
        role = result.scalars().first()
        user = User(
            email=email,
            hashed_password=get_password_hash(password),
            full_name="Test User",
            role_id=role.id,
            is_active=is_active,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    return _create_test_user
