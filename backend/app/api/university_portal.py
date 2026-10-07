from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
import uuid
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime

from app.database import get_db
from app.core.deps import require_permission, get_current_active_user
from app.models.user import User
from app.models.billing import University
from app.models.simulation import Submission
from app.models.enums import OrgType

router = APIRouter(prefix="/api/v1/university", tags=["University Portal"])

class UniversityOut(BaseModel):
    id: uuid.UUID
    name: str
    city: str

    model_config = ConfigDict(from_attributes=True)

class StudentOut(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

class SubmissionSummary(BaseModel):
    task_id: uuid.UUID
    ai_score: Optional[float]
    submitted_at: datetime

    model_config = ConfigDict(from_attributes=True)

class StudentProgressOut(BaseModel):
    student: StudentOut
    submissions: List[SubmissionSummary]

class TopStudent(BaseModel):
    full_name: str
    total_submissions: int
    avg_score: float

class UniversityStats(BaseModel):
    total_students: int
    total_submissions: int
    avg_score: float
    top_students: List[TopStudent]

async def check_university_access(current_user: User, db: AsyncSession):
    if current_user.org_type != OrgType.UNIVERSITY or not current_user.org_id:
        raise HTTPException(status_code=403, detail="Not a university admin")
    
    result = await db.execute(select(University).where(University.id == current_user.org_id))
    university = result.scalars().first()
    if not university:
        raise HTTPException(status_code=403, detail="University not found")
    
    if not university.is_verified:
        raise HTTPException(status_code=403, detail="University not verified yet")
    
    return current_user

@router.get("/list", response_model=List[UniversityOut])
async def list_universities(db: AsyncSession = Depends(get_db)):
    """
    Tasdiqlangan universitetlar ro'yxati — auth talab qilinmaydi, chunki
    frontend'da talaba ro'yxatdan o'tishda o'z universitetini shu
    ro'yxatdan tanlashi kerak (CONTRACT.md: talaba <-> universitet
    bog'lanishi uchun).
    """
    result = await db.execute(select(University).where(University.is_verified == True))  # noqa: E712
    return result.scalars().all()

@router.get("/students", response_model=List[StudentOut])
async def get_students(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("manage_universities"))
):
    current_user = await check_university_access(current_user, db)
    
    result = await db.execute(
        select(User).where(
            User.university_id == current_user.org_id,
        )
    )
    students = result.scalars().all()
    return students

@router.get("/students/{user_id}/progress", response_model=StudentProgressOut)
async def get_student_progress(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("manage_universities"))
):
    current_user = await check_university_access(current_user, db)
    
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.university_id == current_user.org_id,
        )
    )
    student = result.scalars().first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    sub_result = await db.execute(
        select(Submission).where(Submission.user_id == user_id)
    )
    submissions = sub_result.scalars().all()
    
    return StudentProgressOut(
        student=StudentOut.model_validate(student),
        submissions=[
            SubmissionSummary(
                task_id=sub.task_id,
                ai_score=sub.ai_score,
                submitted_at=sub.submitted_at
            ) for sub in submissions
        ]
    )

@router.get("/stats", response_model=UniversityStats)
async def get_university_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("manage_universities"))
):
    current_user = await check_university_access(current_user, db)
    
    students_query = await db.execute(
        select(User).where(
            User.university_id == current_user.org_id,
        )
    )
    students = students_query.scalars().all()
    student_ids = [s.id for s in students]
    total_students = len(students)
    
    if total_students == 0:
        return UniversityStats(
            total_students=0,
            total_submissions=0,
            avg_score=0.0,
            top_students=[]
        )
        
    subs_query = await db.execute(
        select(Submission).where(Submission.user_id.in_(student_ids))
    )
    submissions = subs_query.scalars().all()
    total_submissions = len(submissions)
    
    valid_scores = [s.ai_score for s in submissions if s.ai_score is not None]
    avg_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0.0
    
    student_stats = {}
    for s in students:
        student_stats[s.id] = {"full_name": s.full_name, "subs": 0, "scores": []}
        
    for sub in submissions:
        if sub.user_id in student_stats:
            student_stats[sub.user_id]["subs"] += 1
            if sub.ai_score is not None:
                student_stats[sub.user_id]["scores"].append(sub.ai_score)
                
    top_students_list = []
    for sid, stats in student_stats.items():
        s_avg = sum(stats["scores"]) / len(stats["scores"]) if stats["scores"] else 0.0
        top_students_list.append({
            "full_name": stats["full_name"],
            "total_submissions": stats["subs"],
            "avg_score": s_avg
        })
        
    top_students_list.sort(key=lambda x: (x["avg_score"], x["total_submissions"]), reverse=True)
    
    top_5 = [TopStudent(**ts) for ts in top_students_list[:5]]
    
    return UniversityStats(
        total_students=total_students,
        total_submissions=total_submissions,
        avg_score=avg_score,
        top_students=top_5
    )
