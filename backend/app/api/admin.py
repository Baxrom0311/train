"""
Admin: tashkilot arizalari va umumiy statistika (CONTRACT.md §11.2).
Modul 3 egaligi: backend/app/api/admin.py
"""
import uuid
from datetime import UTC, datetime
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_any_permission, require_permission
from app.database import get_db
from app.models.billing import Company, Invoice, University
from app.models.enums import InvoiceStatus, OrgType
from app.models.user import User

router = APIRouter(prefix="/api/v1/admin", tags=["admin_orgs"])

ORG_MODELS = {OrgType.COMPANY: Company, OrgType.UNIVERSITY: University}


class OrgStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"


class OrgAction(BaseModel):
    org_type: OrgType


class OrgOut(BaseModel):
    id: uuid.UUID
    org_type: OrgType
    name: str
    # kompaniya — soha, universitet — shahar
    detail: str
    contact_email: str
    is_verified: bool
    verified_at: datetime | None
    created_at: datetime
    owner_name: str | None
    owner_email: str | None


class OrgList(BaseModel):
    companies: list[OrgOut]
    universities: list[OrgOut]


class AdminStats(BaseModel):
    pending_companies: int
    pending_universities: int
    verified_companies: int
    verified_universities: int
    invoices_pending: int


async def _owners(db: AsyncSession, org_type: OrgType, ids: list[uuid.UUID]) -> dict[uuid.UUID, User]:
    """Har tashkilotning birinchi ro'yxatdan o'tgan xodimi — arizachi."""
    if not ids:
        return {}
    users = (await db.execute(
        select(User).where(User.org_type == org_type, User.org_id.in_(ids)).order_by(User.created_at)
    )).scalars()
    owners: dict[uuid.UUID, User] = {}
    for u in users:
        owners.setdefault(u.org_id, u)
    return owners


def _out(org: Company | University, org_type: OrgType, owner: User | None) -> OrgOut:
    return OrgOut(
        id=org.id,
        org_type=org_type,
        name=org.name,
        detail=org.industry if org_type == OrgType.COMPANY else org.city,
        contact_email=org.contact_email,
        is_verified=org.is_verified,
        verified_at=org.verified_at,
        created_at=org.created_at,
        owner_name=owner.full_name if owner else None,
        owner_email=owner.email if owner else None,
    )


async def _list(db: AsyncSession, org_type: OrgType, verified: bool) -> list[OrgOut]:
    model = ORG_MODELS[org_type]
    order = model.verified_at.desc() if verified else model.created_at
    orgs = (await db.execute(select(model).where(model.is_verified.is_(verified)).order_by(order))).scalars().all()
    owners = await _owners(db, org_type, [o.id for o in orgs])
    return [_out(o, org_type, owners.get(o.id)) for o in orgs]


async def _org(db: AsyncSession, org_id: uuid.UUID, org_type: OrgType):
    model = ORG_MODELS[org_type]
    org = (await db.execute(select(model).where(model.id == org_id).with_for_update())).scalars().first()
    if org is None:
        raise HTTPException(status_code=404, detail=f"{org_type.value.capitalize()} not found")
    return org


@router.get("/orgs", response_model=OrgList)
async def list_orgs(
    status: OrgStatus = OrgStatus.PENDING,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("approve_companies")),
):
    verified = status == OrgStatus.VERIFIED
    return OrgList(
        companies=await _list(db, OrgType.COMPANY, verified),
        universities=await _list(db, OrgType.UNIVERSITY, verified),
    )


@router.post("/orgs/{org_id}/approve", response_model=OrgOut)
async def approve_org(
    org_id: uuid.UUID,
    data: OrgAction,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("approve_companies")),
):
    org = await _org(db, org_id, data.org_type)
    if not org.is_verified:
        org.is_verified = True
        org.verified_at = datetime.now(UTC)
        org.verified_by_admin_id = user.id
        # register-org'da is_active=False yaratilgan xodimlar faqat shu yerda ochiladi
        pending = await db.execute(
            select(User).where(User.org_type == data.org_type, User.org_id == org_id, User.is_active.is_(False))
        )
        for pending_user in pending.scalars():
            pending_user.is_active = True
        await db.commit()
    owners = await _owners(db, data.org_type, [org.id])
    return _out(org, data.org_type, owners.get(org.id))


@router.post("/orgs/{org_id}/reject", status_code=204)
async def reject_org(
    org_id: uuid.UUID,
    data: OrgAction,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("approve_companies")),
):
    """
    Faqat tasdiqlanmagan ariza. Tashkilot va hech qachon faollashmagan
    xodimlari o'chiriladi — ular tizimda hech narsa yaratmagan (§11.2).
    """
    org = await _org(db, org_id, data.org_type)
    if org.is_verified:
        raise HTTPException(status_code=409, detail="A verified organization cannot be rejected")
    has_active = (await db.execute(
        select(func.count()).select_from(User)
        .where(User.org_type == data.org_type, User.org_id == org_id, User.is_active.is_(True))
    )).scalar_one()
    if has_active:
        raise HTTPException(status_code=409, detail="Organization has active accounts")
    await db.execute(delete(User).where(User.org_type == data.org_type, User.org_id == org_id))
    await db.delete(org)
    await db.commit()


@router.get("/stats", response_model=AdminStats)
async def admin_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_any_permission("approve_companies", "manage_billing")),
):
    """Admin bosh sahifasi uchun."""

    async def count(model, *where) -> int:
        return (await db.execute(select(func.count()).select_from(model).where(*where))).scalar_one()

    return AdminStats(
        pending_companies=await count(Company, Company.is_verified.is_(False)),
        pending_universities=await count(University, University.is_verified.is_(False)),
        verified_companies=await count(Company, Company.is_verified.is_(True)),
        verified_universities=await count(University, University.is_verified.is_(True)),
        invoices_pending=await count(Invoice, Invoice.status == InvoiceStatus.PENDING),
    )
