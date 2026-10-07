"""
Admin paneli: tashkilot arizalari, statistika, invoice'lar (CONTRACT.md §11).
"""
import uuid

import pytest
from sqlalchemy import select

from app.models.billing import Company, Invoice, University
from app.models.user import User

pytestmark = pytest.mark.asyncio


async def _headers(client, factory, email, role):
    await factory(email, "pass", role)
    r = await client.post("/api/v1/auth/login", data={"username": email, "password": "pass"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
async def admin(client, test_user_factory):
    return await _headers(client, test_user_factory, "admin@tryjob.test", "admin")


async def _apply(client, email, org_type, name):
    body = {"email": email, "password": "pass12345", "full_name": "Ariza Beruvchi", "org_type": org_type,
            "org_name": name, "industry": "Fintech", "city": "Samarqand"}
    r = await client.post("/api/v1/auth/register-org", json=body)
    assert r.status_code == 202


async def _company(db, name="Kumush Fintech", verified=True):
    company = Company(name=name, industry="Fintech", contact_email="hr@kumush.uz", is_verified=verified)
    db.add(company)
    await db.commit()
    return company


# ── Arizalar ─────────────────────────────────────────────────────────


async def test_pending_list_shows_applicant(client, admin):
    await _apply(client, "hr@kumush.uz", "company", "Kumush Fintech")
    await _apply(client, "dean@samdu.uz", "university", "Samarqand Davlat Universiteti")

    data = (await client.get("/api/v1/admin/orgs", headers=admin)).json()
    [company], [uni] = data["companies"], data["universities"]
    assert company["owner_email"] == "hr@kumush.uz" and company["detail"] == "Fintech"
    assert uni["name"] == "Samarqand Davlat Universiteti" and uni["detail"] == "Samarqand"
    assert (await client.get("/api/v1/admin/orgs?status=verified", headers=admin)).json() == {
        "companies": [], "universities": []
    }


async def test_approve_then_login(client, admin):
    await _apply(client, "hr@kumush.uz", "company", "Kumush Fintech")
    login = {"username": "hr@kumush.uz", "password": "pass12345"}
    assert (await client.post("/api/v1/auth/login", data=login)).status_code == 403

    org_id = (await client.get("/api/v1/admin/orgs", headers=admin)).json()["companies"][0]["id"]
    r = await client.post(f"/api/v1/admin/orgs/{org_id}/approve", headers=admin, json={"org_type": "company"})
    assert r.status_code == 200 and r.json()["is_verified"] is True
    # takroriy tasdiqlash — o'zgarishsiz
    r = await client.post(f"/api/v1/admin/orgs/{org_id}/approve", headers=admin, json={"org_type": "company"})
    assert r.status_code == 200

    assert (await client.post("/api/v1/auth/login", data=login)).status_code == 200
    verified = (await client.get("/api/v1/admin/orgs?status=verified", headers=admin)).json()
    assert [c["id"] for c in verified["companies"]] == [org_id]


async def test_reject_removes_application(client, db_session, admin):
    await _apply(client, "spam@spam.uz", "company", "Spam LLC")
    org_id = (await client.get("/api/v1/admin/orgs", headers=admin)).json()["companies"][0]["id"]
    r = await client.post(f"/api/v1/admin/orgs/{org_id}/reject", headers=admin, json={"org_type": "company"})
    assert r.status_code == 204

    assert (await db_session.execute(select(Company))).scalars().first() is None
    assert (await db_session.execute(select(User).where(User.email == "spam@spam.uz"))).scalars().first() is None
    # nom bo'shadi — qayta ariza berish mumkin
    await _apply(client, "real@spam.uz", "company", "Spam LLC")


async def test_cannot_reject_verified(client, db_session, admin):
    company = await _company(db_session)
    r = await client.post(f"/api/v1/admin/orgs/{company.id}/reject", headers=admin, json={"org_type": "company"})
    assert r.status_code == 409
    r = await client.post(f"/api/v1/admin/orgs/{uuid.uuid4()}/reject", headers=admin, json={"org_type": "company"})
    assert r.status_code == 404


async def test_only_admin(client, test_user_factory):
    student = await _headers(client, test_user_factory, "s@test.uz", "student")
    hr = await _headers(client, test_user_factory, "hr@test.uz", "company_hr")
    for h in (student, hr):
        assert (await client.get("/api/v1/admin/orgs", headers=h)).status_code == 403
        assert (await client.get("/api/v1/admin/stats", headers=h)).status_code == 403
        assert (await client.get("/api/v1/admin/invoices", headers=h)).status_code == 403


async def test_stats(client, db_session, admin):
    await _apply(client, "hr@alpha.uz", "company", "Alpha")
    company = await _company(db_session)
    await client.post("/api/v1/admin/invoices", headers=admin,
                      json={"payer_type": "company", "payer_id": str(company.id), "amount": "1000"})
    assert (await client.get("/api/v1/admin/stats", headers=admin)).json() == {
        "pending_companies": 1, "pending_universities": 0,
        "verified_companies": 1, "verified_universities": 0, "invoices_pending": 1,
    }


# ── Invoice'lar ──────────────────────────────────────────────────────


async def test_invoice_only_for_verified_payer(client, db_session, admin):
    pending = await _company(db_session, "Pending Co", verified=False)
    body = {"payer_type": "company", "payer_id": str(pending.id), "amount": "1500000"}
    assert (await client.post("/api/v1/admin/invoices", headers=admin, json=body)).status_code == 400
    body["payer_id"] = str(uuid.uuid4())
    assert (await client.post("/api/v1/admin/invoices", headers=admin, json=body)).status_code == 404


@pytest.mark.parametrize("amount,currency", [("0", "UZS"), ("-5", "UZS"), ("10.001", "UZS"), ("10", "EUR")])
async def test_invoice_validation(client, db_session, admin, amount, currency):
    company = await _company(db_session)
    body = {"payer_type": "company", "payer_id": str(company.id), "amount": amount, "currency": currency}
    assert (await client.post("/api/v1/admin/invoices", headers=admin, json=body)).status_code == 422


async def test_invoice_lifecycle(client, db_session, admin):
    company = await _company(db_session)
    body = {"payer_type": "company", "payer_id": str(company.id), "amount": "2500000.50", "notes": " Oktabr "}
    r = await client.post("/api/v1/admin/invoices", headers=admin, json=body)
    assert r.status_code == 201
    inv = r.json()
    assert inv["payer_name"] == "Kumush Fintech" and inv["amount"] == "2500000.50" and inv["notes"] == "Oktabr"

    paid = (await client.post(f"/api/v1/admin/invoices/{inv['id']}/mark-paid", headers=admin)).json()
    assert paid["status"] == "paid" and paid["paid_marked_at"]
    again = (await client.post(f"/api/v1/admin/invoices/{inv['id']}/mark-paid", headers=admin)).json()
    assert again["paid_marked_at"] == paid["paid_marked_at"]
    assert (await client.post(f"/api/v1/admin/invoices/{inv['id']}/cancel", headers=admin)).status_code == 409

    second = (await client.post("/api/v1/admin/invoices", headers=admin, json=body)).json()
    assert (await client.post(f"/api/v1/admin/invoices/{second['id']}/cancel", headers=admin)).json()["status"] == "cancelled"
    assert (await client.post(f"/api/v1/admin/invoices/{second['id']}/mark-paid", headers=admin)).status_code == 409

    listed = (await client.get("/api/v1/admin/invoices", headers=admin)).json()
    assert [i["id"] for i in listed] == [second["id"], inv["id"]]
    assert [i["id"] for i in (await client.get("/api/v1/admin/invoices?status=paid", headers=admin)).json()] == [inv["id"]]
    assert (await client.get("/api/v1/admin/invoices?payer_type=university", headers=admin)).json() == []


async def test_org_sees_only_own_invoices(client, db_session, test_user_factory, admin):
    mine = await _company(db_session, "Mine")
    other = await _company(db_session, "Other")
    uni = University(name="Uni", city="Toshkent", contact_email="u@u.test", is_verified=True)
    db_session.add(uni)
    await db_session.commit()
    for payer_type, org in (("company", mine), ("company", other), ("university", uni)):
        await client.post("/api/v1/admin/invoices", headers=admin,
                          json={"payer_type": payer_type, "payer_id": str(org.id), "amount": "100"})

    hr_user = await test_user_factory("hr@mine.test", "pass", "company_hr")
    hr_user.org_type, hr_user.org_id = "company", mine.id
    await db_session.commit()
    r = await client.post("/api/v1/auth/login", data={"username": "hr@mine.test", "password": "pass"})
    hr = {"Authorization": f"Bearer {r.json()['access_token']}"}

    own = (await client.get("/api/v1/billing/invoices", headers=hr)).json()
    assert [i["payer_name"] for i in own] == ["Mine"]
    student = await _headers(client, test_user_factory, "st@test.uz", "student")
    assert (await client.get("/api/v1/billing/invoices", headers=student)).status_code == 403
    assert len((await db_session.execute(select(Invoice))).scalars().all()) == 3
