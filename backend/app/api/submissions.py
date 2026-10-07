import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.simulation import Submission, SimulationTask
from app.core.deps import get_current_active_user
from app.models.user import User
from app.ai.router import evaluate_submission
from app.models.enums import AIEvalStatus

router = APIRouter(tags=["submissions"])

class SubmissionCreate(BaseModel):
    task_id: uuid.UUID
    content: str

class SubmissionOut(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    user_id: uuid.UUID
    content: str
    ai_score: float | None = None
    ai_feedback: str | None = None
    ai_eval_status: AIEvalStatus
    submitted_at: datetime
    evaluated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

@router.post("/submissions", response_model=SubmissionOut, status_code=status.HTTP_201_CREATED)
async def create_submission(
    sub_in: SubmissionCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user)
):
    # check if task exists
    task_res = await db.execute(select(SimulationTask).where(SimulationTask.id == sub_in.task_id))
    if not task_res.scalars().first():
        raise HTTPException(status_code=404, detail="Task not found")

    submission = Submission(
        task_id=sub_in.task_id,
        user_id=user.id,
        content=sub_in.content
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    # Trigger AI Evaluation
    await evaluate_submission(submission, db)
    await db.refresh(submission)

    return submission

@router.get("/submissions/my", response_model=List[SubmissionOut])
async def list_my_submissions(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(Submission).where(Submission.user_id == user.id))
    return result.scalars().all()

@router.get("/submissions/{id}", response_model=SubmissionOut)
async def get_submission(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(Submission).where(Submission.id == id, Submission.user_id == user.id))
    sub = result.scalars().first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    return sub
