import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models.case_cup import CaseCup, CaseCupSubmission
from app.models.user import User
from app.core.deps import get_current_active_user, require_permission
from app.ai.router import evaluate_submission

router = APIRouter(prefix="/case-cups", tags=["Case Cups"])

class CaseCupCreate(BaseModel):
    title: str
    description: str
    company_id: uuid.UUID
    sector: str
    start_date: datetime
    end_date: datetime
    is_active: bool = True

class CaseCupOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    company_id: uuid.UUID
    sector: str
    start_date: datetime
    end_date: datetime
    is_active: bool
    created_by_admin_id: Optional[uuid.UUID]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class CaseCupSubmissionCreate(BaseModel):
    content: str

class CaseCupSubmissionOut(BaseModel):
    id: uuid.UUID
    case_cup_id: uuid.UUID
    user_id: uuid.UUID
    content: str
    ai_score: Optional[float]
    ai_feedback: Optional[str]
    submitted_at: datetime
    rank: Optional[int]

    model_config = ConfigDict(from_attributes=True)

class LeaderboardEntry(BaseModel):
    rank: int
    full_name: str
    ai_score: float
    submitted_at: datetime

@router.get("", response_model=List[CaseCupOut])
async def list_case_cups(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(CaseCup).where(CaseCup.is_active == True))
    return result.scalars().all()

@router.get("/{id}", response_model=CaseCupOut)
async def get_case_cup(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(CaseCup).where(CaseCup.id == id))
    cc = result.scalars().first()
    if not cc:
        raise HTTPException(status_code=404, detail="Not found")
    return cc

@router.post("", response_model=CaseCupOut, status_code=status.HTTP_201_CREATED)
async def create_case_cup(
    cc_in: CaseCupCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("manage_simulations"))
):
    cc = CaseCup(**cc_in.model_dump(), created_by_admin_id=admin.id)
    db.add(cc)
    await db.commit()
    await db.refresh(cc)
    return cc

@router.post("/{id}/submit", response_model=CaseCupSubmissionOut, status_code=status.HTTP_201_CREATED)
async def submit_case_cup(
    id: uuid.UUID,
    sub_in: CaseCupSubmissionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    cc = await db.get(CaseCup, id)
    if not cc:
        raise HTTPException(status_code=404, detail="Not found")
        
    sub = CaseCupSubmission(
        case_cup_id=id,
        user_id=current_user.id,
        content=sub_in.content
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    
    # Run eval
    await evaluate_submission(sub, db)
    await db.refresh(sub)
    
    return sub

@router.get("/{id}/leaderboard", response_model=List[LeaderboardEntry])
async def get_leaderboard(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    stmt = (
        select(CaseCupSubmission, User)
        .join(User, CaseCupSubmission.user_id == User.id)
        .where(CaseCupSubmission.case_cup_id == id)
        .where(CaseCupSubmission.ai_score.is_not(None))
        .order_by(desc(CaseCupSubmission.ai_score))
        .limit(10)
    )
    result = await db.execute(stmt)
    rows = result.all()
    
    leaderboard = []
    for rank_idx, (sub, user) in enumerate(rows, start=1):
        leaderboard.append(LeaderboardEntry(
            rank=rank_idx,
            full_name=user.full_name,
            ai_score=sub.ai_score,
            submitted_at=sub.submitted_at
        ))
    return leaderboard
