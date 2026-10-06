import uuid
from datetime import datetime
from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, String, cast

from app.database import get_db
from app.models.user import User, CandidateVisibility
from app.models.billing import Company
from app.models.simulation import Submission
from app.models.talent import TalentOffer
from app.core.deps import get_current_active_user, require_permission

router = APIRouter(prefix="/talents", tags=["Talent Hunt"])

class CandidateOut(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str
    completed_simulations: int

    class Config:
        from_attributes = True

class TalentOfferCreate(BaseModel):
    candidate_id: uuid.UUID
    message: str

class TalentOfferOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    candidate_id: uuid.UUID
    message: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

@router.get("", response_model=List[CandidateOut])
async def get_talents(
    current_user: Annotated[User, Depends(require_permission("view_candidates"))],
    db: AsyncSession = Depends(get_db)
):
    if current_user.org_type != "company" or not current_user.org_id:
        raise HTTPException(status_code=403, detail="Only company users can view candidates")
    
    company = await db.get(Company, current_user.org_id)
    if not company or not company.is_verified:
        raise HTTPException(status_code=403, detail="Company is not verified")
    
    # Subquery for completed submissions
    subq = select(Submission.user_id, func.count(Submission.id).label("completed_simulations")).group_by(Submission.user_id).subquery()
    
    query = (
        select(User, func.coalesce(subq.c.completed_simulations, 0).label("completed_simulations"))
        .join(CandidateVisibility, User.id == CandidateVisibility.user_id)
        .outerjoin(subq, User.id == subq.c.user_id)
        .where(CandidateVisibility.is_open_to_work == True)
        .where(~cast(CandidateVisibility.hidden_from_company_ids, String).contains(str(current_user.org_id)))
    )
    
    result = await db.execute(query)
    rows = result.all()
    
    candidates = []
    for user, completed_simulations in rows:
        candidates.append(CandidateOut(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            completed_simulations=completed_simulations
        ))
        
    return candidates

@router.post("/offers", response_model=TalentOfferOut)
async def create_talent_offer(
    offer_in: TalentOfferCreate,
    current_user: Annotated[User, Depends(require_permission("view_candidates"))],
    db: AsyncSession = Depends(get_db)
):
    if current_user.org_type != "company" or not current_user.org_id:
        raise HTTPException(status_code=403, detail="Only company users can send offers")
    
    company = await db.get(Company, current_user.org_id)
    if not company or not company.is_verified:
        raise HTTPException(status_code=403, detail="Company is not verified")
    
    offer = TalentOffer(
        company_id=current_user.org_id,
        candidate_id=offer_in.candidate_id,
        message=offer_in.message
    )
    db.add(offer)
    await db.commit()
    await db.refresh(offer)
    
    return offer

@router.get("/offers/my", response_model=List[TalentOfferOut])
async def get_my_offers(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db)
):
    query = select(TalentOffer).where(TalentOffer.candidate_id == current_user.id)
    result = await db.execute(query)
    offers = result.scalars().all()
    
    return offers
