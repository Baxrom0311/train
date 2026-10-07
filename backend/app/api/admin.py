"""
Admin: tashkilot arizalari va umumiy statistika (CONTRACT.md §11.2),
platforma statistikasi va AI sarfi (§21).
Modul 3 egaligi: backend/app/api/admin.py
"""
import asyncio
import logging
import uuid
from datetime import UTC, date, datetime
from enum import Enum

from arq.constants import default_queue_name
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import platform
from app.core.deps import require_any_permission, require_permission
from app.database import get_db
from app.models.billing import Company, Invoice, University
from app.models.enums import InvoiceStatus, OrgType
from app.models.user import User

router = APIRouter(prefix="/api/v1/admin", tags=["admin_orgs"])
log = logging.getLogger(__name__)
PLATFORM_PERIODS = (7, 30, 90)   # §21.3

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


class PlatformUsers(BaseModel):
    students: int
    companies: int
    universities: int
    new_students: int
    active_students: int


class PlatformRuns(BaseModel):
    in_progress: int
    started: int
    completed: int
    expired: int
    abandoned: int
    completion_rate: float | None
    avg_score: float | None


class PlatformEvaluation(BaseModel):
    pending: int
    queued_retry: int
    failed: int
    oldest_pending_minutes: int | None
    queue_jobs: int | None


class AIPurpose(BaseModel):
    purpose: str
    calls: int
    tokens: int
    cost_usd: float | None


class AIProvider(BaseModel):
    provider: str
    model: str
    calls: int
    failures: int
    tokens_in: int
    tokens_out: int
    cost_usd: float | None


class PlatformAI(BaseModel):
    calls: int
    failures: int
    tokens_in: int
    tokens_out: int
    cost_usd: float | None
    cost_complete: bool
    by_purpose: list[AIPurpose]
    by_provider: list[AIProvider]


class PlatformDay(BaseModel):
    day: date
    new_students: int
    runs_started: int
    runs_completed: int
    ai_tokens: int
    ai_cost_usd: float | None


class PlatformScenario(BaseModel):
    scenario_id: uuid.UUID
    title: str
    sector: str
    started: int
    completed: int
    completion_rate: float | None
    avg_score: float | None


class PlatformStats(BaseModel):
    generated_at: datetime
    days: int
    users: PlatformUsers
    runs: PlatformRuns
    evaluation: PlatformEvaluation
    ai: PlatformAI
    daily: list[PlatformDay]
    scenarios: list[PlatformScenario]


async def _queue_jobs() -> int | None:
    """arq navbatidagi ishlar; Redis javob bermasa — None (statistika baribir chiqadi)."""
    from app.core.redis_client import redis_client

    try:
        return await asyncio.wait_for(redis_client.zcard(default_queue_name), 2.0)
    except Exception as exc:  # noqa: BLE001
        log.warning("arq navbati o'qilmadi: %s", exc)
        return None


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


@router.get("/platform", response_model=PlatformStats)
async def platform_stats(
    days: int = Query(default=30),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("view_platform_stats")),
):
    """Foydalanuvchilar, Run'lar, baholash navbati va AI sarfi (§21.3)."""
    if days not in PLATFORM_PERIODS:
        raise HTTPException(status_code=422, detail=f"days must be one of {PLATFORM_PERIODS}")
    return await platform.build(db, days, datetime.now(UTC), await _queue_jobs())
