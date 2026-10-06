import pytest
from httpx import AsyncClient
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, UTC

from app.main import app
from app.api.admin import router as admin_router
from app.api.billing import router as billing_router
from app.models.billing import Company, Invoice
from app.core.security import create_access_token

# Attempt to include routers, ignore if already included
try:
    app.include_router(admin_router)
except Exception:
    pass
try:
    app.include_router(billing_router)
except Exception:
    pass

@pytest.fixture
async def unverified_company(db_session: AsyncSession):
    company = Company(
        id=uuid.uuid4(),
        name=f"Atlas Global Finance {uuid.uuid4()}",
        industry="Finance",
        contact_email="test@atlas.com"
    )
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)
    return company

@pytest.fixture
async def token_student(test_user_factory):
    user = await test_user_factory(email="student@test.com", password="pwd", role_name="student")
    return create_access_token(user.id)

@pytest.fixture
async def token_admin(test_user_factory):
    user = await test_user_factory(email="admin@test.com", password="pwd", role_name="admin")
    return create_access_token(user.id)

@pytest.mark.asyncio
async def test_approve_org_forbidden(client: AsyncClient, token_student: str, unverified_company: Company):
    res = await client.post(
        f"/api/v1/admin/orgs/{unverified_company.id}/approve",
        headers={"Authorization": f"Bearer {token_student}"},
        json={"org_type": "company"}
    )
    assert res.status_code == 403

@pytest.mark.asyncio
async def test_approve_company(client: AsyncClient, token_admin: str, unverified_company: Company, db_session: AsyncSession):
    res = await client.post(
        f"/api/v1/admin/orgs/{unverified_company.id}/approve",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={"org_type": "company"}
    )
    assert res.status_code == 200
    
    await db_session.refresh(unverified_company)
    assert unverified_company.is_verified is True
    assert unverified_company.verified_at is not None
    assert unverified_company.verified_by_admin_id is not None

@pytest.mark.asyncio
async def test_create_invoice_admin(client: AsyncClient, token_admin: str, unverified_company: Company):
    res = await client.post(
        "/api/v1/admin/invoices",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={
            "payer_type": "company",
            "payer_id": str(unverified_company.id),
            "amount": 100000.0,
            "currency": "UZS",
            "notes": "Test invoice"
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["amount"] == 100000.0
    assert data["status"] == "pending"

@pytest.mark.asyncio
async def test_mark_invoice_paid(client: AsyncClient, token_admin: str, unverified_company: Company, db_session: AsyncSession):
    res_create = await client.post(
        "/api/v1/admin/invoices",
        headers={"Authorization": f"Bearer {token_admin}"},
        json={
            "payer_type": "company",
            "payer_id": str(unverified_company.id),
            "amount": 50000.0,
            "currency": "UZS",
            "notes": "Test invoice to mark paid"
        }
    )
    assert res_create.status_code == 200
    invoice_id = res_create.json()["id"]
    
    res_paid = await client.post(
        f"/api/v1/admin/invoices/{invoice_id}/mark-paid",
        headers={"Authorization": f"Bearer {token_admin}"}
    )
    
    assert res_paid.status_code == 200
    data = res_paid.json()
    assert data["status"] == "paid"
    assert data["paid_marked_at"] is not None
