from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Union
from pydantic import BaseModel, ConfigDict
from datetime import datetime, UTC
import uuid

from app.database import get_db
from app.core.deps import require_permission
from app.models.user import User
from app.models.billing import Company, University
from app.models.enums import OrgType

router = APIRouter(prefix="/api/v1/admin/orgs", tags=["admin_orgs"])

class OrgApproveIn(BaseModel):
    org_type: OrgType

class CompanyOut(BaseModel):
    id: uuid.UUID
    name: str
    industry: str
    contact_email: str
    is_verified: bool
    verified_at: datetime | None = None
    verified_by_admin_id: uuid.UUID | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class UniversityOut(BaseModel):
    id: uuid.UUID
    name: str
    city: str
    contact_email: str
    is_verified: bool
    verified_at: datetime | None = None
    verified_by_admin_id: uuid.UUID | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

@router.get("", response_model=dict[str, list[Union[CompanyOut, UniversityOut]]])
async def get_unverified_orgs(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("approve_companies"))
):
    companies_stmt = select(Company).where(Company.is_verified == False)
    companies_result = await db.execute(companies_stmt)
    companies = companies_result.scalars().all()
    
    unis_stmt = select(University).where(University.is_verified == False)
    unis_result = await db.execute(unis_stmt)
    unis = unis_result.scalars().all()
    
    return {
        "companies": companies,
        "universities": unis
    }

@router.post("/{org_id}/approve")
async def approve_org(
    org_id: uuid.UUID,
    data: OrgApproveIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("approve_companies"))
):
    model = Company if data.org_type == OrgType.COMPANY else University
    stmt = select(model).where(model.id == org_id)
    result = await db.execute(stmt)
    org = result.scalars().first()

    if not org:
        raise HTTPException(status_code=404, detail=f"{data.org_type.value.capitalize()} not found")
        
    if org.is_verified:
        return {"msg": "Already verified"}

    org.is_verified = True
    org.verified_at = datetime.now(UTC)
    org.verified_by_admin_id = user.id

    # Tashkilot tasdiqlangach, unga tegishli (hali faollashtirilmagan)
    # foydalanuvchilarni ham faollashtirish shart — aks holda is_active=False
    # bilan yaratilgan HR/universitet admin akkaunti HECH QACHON kira
    # olmasdi (register-org'da is_active=False qilib yaratilgan,
    # avvalgi versiyada shu yerda hech kim faollashtirmagan edi).
    users_stmt = select(User).where(
        User.org_type == data.org_type,
        User.org_id == org_id,
        User.is_active == False,  # noqa: E712
    )
    users_result = await db.execute(users_stmt)
    for pending_user in users_result.scalars().all():
        pending_user.is_active = True

    await db.commit()

    return {"msg": "Approved successfully"}
