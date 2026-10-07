"""
Talent Hunt API — CONTRACT.md §7 va docs/tasks/04-talent-hunt.md bo'yicha.
Modul 4 egaligi: backend/app/api/talent_hunt.py
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, String
from sqlalchemy.dialects.postgresql import JSONB

from app.database import get_db
from app.models.user import User
from app.models.talent import CandidateVisibility, TalentOffer
from app.models.billing import Company
from app.models.simulation import Submission
from app.core.deps import get_current_active_user, require_permission
from app.models.enums import OrgType, TalentOfferStatus

router = APIRouter(prefix="/api/v1/talents", tags=["Talent Hunt"])
# /api/v1/users/... endpointlar uchun alohida router (main.py users_router ni topadi)
users_router = APIRouter(prefix="/api/v1/users", tags=["Talent Hunt - Visibility"])


# ---------------------------------------------------------------------------
# Schemalar
# ---------------------------------------------------------------------------

class VisibilityUpdate(BaseModel):
    is_open_to_work: bool
    hidden_from_company_ids: List[str] = []


class VisibilityOut(BaseModel):
    user_id: uuid.UUID
    is_open_to_work: bool
    hidden_from_company_ids: List[str]

    model_config = ConfigDict(from_attributes=True)


class CandidateOut(BaseModel):
    """
    Kontakt ma'lumotlari (email/tel) ko'rsatilmaydi — faqat TalentOffer
    yuborilgandan so'ng ochiladi (CONTRACT.md §7 va 04-talent-hunt.md §2).
    """
    id: uuid.UUID
    full_name: str
    completed_simulations: int

    model_config = ConfigDict(from_attributes=True)


class TalentOfferCreate(BaseModel):
    candidate_user_id: uuid.UUID
    position_title: str
    message: str


class TalentOfferOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    candidate_user_id: uuid.UUID
    position_title: str
    message: str
    status: TalentOfferStatus
    respond_due_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# PATCH /users/me/visibility  — faqat o'zi
# ---------------------------------------------------------------------------

@users_router.patch("/me/visibility", response_model=VisibilityOut)
async def update_my_visibility(
    body: VisibilityUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
):
    """Talaba o'zining ko'rinishini boshqaradi (CONTRACT.md §7)."""
    result = await db.execute(
        select(CandidateVisibility).where(CandidateVisibility.user_id == current_user.id)
    )
    vis = result.scalars().first()

    if vis is None:
        vis = CandidateVisibility(
            user_id=current_user.id,
            is_open_to_work=body.is_open_to_work,
            hidden_from_company_ids=body.hidden_from_company_ids,
        )
        db.add(vis)
    else:
        vis.is_open_to_work = body.is_open_to_work
        vis.hidden_from_company_ids = body.hidden_from_company_ids
        vis.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(vis)
    return vis


# ---------------------------------------------------------------------------
# GET /talents — faqat tasdiqlangan kompaniya + faqat ochiq nomzodlar
# ---------------------------------------------------------------------------

@router.get("", response_model=List[CandidateOut])
async def get_talents(
    current_user: Annotated[User, Depends(require_permission("view_candidates"))],
    db: AsyncSession = Depends(get_db),
):
    """
    Faqat is_open_to_work=True va shu kompaniya hidden_from_company_ids'da
    bo'lmagan nomzodlarni qaytaradi.
    CandidateVisibility yozuvi yo'q = ko'rinmaydi (yo'q yozuv = yopiq).
    """
    if current_user.org_type != OrgType.COMPANY or not current_user.org_id:
        raise HTTPException(status_code=403, detail="Only company users can view candidates")

    company = await db.get(Company, current_user.org_id)
    if not company or not company.is_verified:
        raise HTTPException(status_code=403, detail="Company is not verified")

    company_id_str = str(current_user.org_id)

    # Tugallangan simulyatsiyalar soni subquery
    subq = (
        select(Submission.user_id, func.count(Submission.id).label("cnt"))
        .group_by(Submission.user_id)
        .subquery()
    )

    # INNER JOIN — CandidateVisibility yozuvi yo'q nomzodlar chiqmaydi
    query = (
        select(User, func.coalesce(subq.c.cnt, 0).label("completed_simulations"))
        .join(CandidateVisibility, User.id == CandidateVisibility.user_id)  # INNER JOIN
        .outerjoin(subq, User.id == subq.c.user_id)
        .where(CandidateVisibility.is_open_to_work == True)  # noqa: E712
        .where(
            # PostgreSQL JSON massivida kompaniya ID si yo'qligini tekshiramiz
            ~func.cast(CandidateVisibility.hidden_from_company_ids, String).contains(company_id_str)
        )
    )

    result = await db.execute(query)
    rows = result.all()

    return [
        CandidateOut(
            id=user.id,
            full_name=user.full_name,
            completed_simulations=completed,
        )
        for user, completed in rows
    ]


# ---------------------------------------------------------------------------
# POST /talents/offers — offer yuborish
# ---------------------------------------------------------------------------

@router.post("/offers", response_model=TalentOfferOut)
async def create_talent_offer(
    offer_in: TalentOfferCreate,
    current_user: Annotated[User, Depends(require_permission("view_candidates"))],
    db: AsyncSession = Depends(get_db),
):
    """
    Faqat ko'rinish shartlariga mos nomzodga offer yuboriladi.
    Yashirilgan yoki mavjud bo'lmagan nomzodga 404 — 403 EMAS
    (04-talent-hunt.md §2: yashiringanini bildirmaslik kerak).
    """
    if current_user.org_type != OrgType.COMPANY or not current_user.org_id:
        raise HTTPException(status_code=403, detail="Only company users can send offers")

    company = await db.get(Company, current_user.org_id)
    if not company or not company.is_verified:
        raise HTTPException(status_code=403, detail="Company is not verified")

    company_id_str = str(current_user.org_id)

    # Nomzod ko'rinish shartlarini tekshirish (INNER JOIN orqali)
    vis_result = await db.execute(
        select(CandidateVisibility).where(
            CandidateVisibility.user_id == offer_in.candidate_user_id,
            CandidateVisibility.is_open_to_work == True,  # noqa: E712
        )
    )
    vis = vis_result.scalars().first()

    # Yo'q yoki yopiq yoki yashirilgan — barchasi 404 (leak yo'q)
    if vis is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    if company_id_str in (vis.hidden_from_company_ids or []):
        raise HTTPException(status_code=404, detail="Candidate not found")

    # respond_due_at = hozir + 5 ish kuni (taxminiy: 7 kalendar kun)
    respond_due_at = datetime.now(timezone.utc) + timedelta(days=7)

    offer = TalentOffer(
        company_id=current_user.org_id,
        candidate_user_id=offer_in.candidate_user_id,
        position_title=offer_in.position_title,
        message=offer_in.message,
        respond_due_at=respond_due_at,
    )
    db.add(offer)
    await db.commit()
    await db.refresh(offer)
    return offer


# ---------------------------------------------------------------------------
# GET /talents/offers/my — talabaning o'ziga kelgan offerlar
# ---------------------------------------------------------------------------

@router.get("/offers/my", response_model=List[TalentOfferOut])
async def get_my_offers(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
):
    """Talabaga yuborilgan offerlar ro'yxati."""
    result = await db.execute(
        select(TalentOffer).where(TalentOffer.candidate_user_id == current_user.id)
    )
    return result.scalars().all()
