import math
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Submission, SimulationTask, Simulation, DynamicChallenge
from app.schemas import SubmissionOut
from app.api.auth import get_current_user
from app.core.file_validator import validate_and_save_upload
from app.core.security import sanitize_text
from app.ai.router import ai_router
from app.ai.adaptive_engine import LEVEL_DEFINITIONS

router = APIRouter(prefix="/submissions", tags=["Submissions & Evaluation"])

def _calculate_elo_delta(user_elo: int, task_level: int, score_pct: float) -> int:
    """
    Standart FIDE ELO algoritmi asosida talabaning yangi ELO o'zgarishini hisoblash.
    """
    task_elo = 1000 + (task_level - 1) * 150
    expected_score = 1.0 / (1.0 + math.pow(10.0, (task_elo - user_elo) / 400.0))
    actual_score = max(0.0, min(1.0, score_pct / 100.0))
    
    k_factor = 32 if user_elo < 1600 else (24 if user_elo < 2000 else 16)
    delta = int(round(k_factor * (actual_score - expected_score)))
    
    # Agar 90% dan yuqori ball bilan topshirsa bonus
    if score_pct >= 90.0 and delta >= 0:
        delta += 5
    elif score_pct >= 80.0 and delta >= 0:
        delta += 2
        
    return delta

@router.post("", response_model=SubmissionOut)
async def create_submission(
    task_id: Optional[str] = Form(None),
    dynamic_challenge_id: Optional[str] = Form(None),
    simulation_id: str = Form(...),
    submitted_text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Talaba topshirig'ini qabul qilish va AI Mentor / Kengaytirilgan AST orqali baholash.
    Standart simulyatsiya topshiriqlari va Dinamik Adaptiv Topsiriqlar (Infinite Engine)
    uchun talabaning Mastery Level va ELO reytingini avtomatik oshirib boradi.
    """
    task = None
    dyn_challenge = None
    
    # 1. Topshiriq yoki Dinamik Challenjeni aniqlash
    if dynamic_challenge_id:
        dyn_challenge = db.query(DynamicChallenge).filter(
            DynamicChallenge.id == dynamic_challenge_id,
            DynamicChallenge.user_id == current_user.id
        ).first()
        if not dyn_challenge:
            raise HTTPException(status_code=404, detail="Dinamik topshiriq topilmadi")
    elif task_id:
        task = db.query(SimulationTask).filter(SimulationTask.id == task_id).first()
        if not task:
            # Agar task_id dynamic challenge id sifatida yuborilgan bo'lsa
            dyn_challenge = db.query(DynamicChallenge).filter(
                DynamicChallenge.id == task_id,
                DynamicChallenge.user_id == current_user.id
            ).first()
            if not dyn_challenge:
                raise HTTPException(status_code=404, detail="Topshiriq topilmadi")
    else:
        raise HTTPException(status_code=400, detail="task_id yoki dynamic_challenge_id ko'rsatilishi shart")

    # Fayl mavjud bo'lsa xavfsiz yuklab olish
    attachment_path = None
    if file and file.filename:
        attachment_path = await validate_and_save_upload(file)

    clean_text = sanitize_text(submitted_text)
    if not clean_text and not attachment_path:
        raise HTTPException(status_code=400, detail="Topshiriq matni yoki fayl yuklanishi shart")

    user_text_payload = clean_text or f"Yuklangan fayl: {attachment_path}"

    # 2. AI & AST Evaluator orqali baholash
    if dyn_challenge:
        feedback = await ai_router.evaluate_submission(
            task_title=dyn_challenge.title,
            briefing=dyn_challenge.briefing,
            instructions=dyn_challenge.instructions,
            rubric=dyn_challenge.rubric_criteria or [],
            model_answer=dyn_challenge.model_answer,
            user_submission_text=user_text_payload,
            mentor_persona_key=dyn_challenge.mentor_persona,
            level=dyn_challenge.level,
            challenge_type=dyn_challenge.challenge_type,
            synthetic_dataset=dyn_challenge.synthetic_dataset
        )
        task_level = dyn_challenge.level
    else:
        feedback = await ai_router.evaluate_submission(
            task_title=task.title,
            briefing=task.briefing_text,
            instructions=task.instructions,
            rubric=task.rubric_criteria or [],
            model_answer=task.model_answer,
            user_submission_text=user_text_payload,
            mentor_persona_key=task.mentor_persona,
            level=1
        )
        task_level = 1

    # 3. ELO va Mastery Level hisoblash
    current_elo = current_user.elo_rating or 1000
    elo_delta = _calculate_elo_delta(current_elo, task_level, feedback.total_score)
    new_elo = max(500, current_elo + elo_delta)
    new_mastery_level = max(1, 1 + (new_elo - 1000) // 150)
    xp_earned = max(10, int(feedback.total_score * (1.5 + task_level * 0.5)))

    # Foydalanuvchi ko'rsatkichlarini yangilash
    current_user.elo_rating = new_elo
    current_user.mastery_level = new_mastery_level
    current_user.xp_points = (current_user.xp_points or 0) + xp_earned
    
    # Adaptive skill profile yangilash
    skill_profile = current_user.adaptive_skill_profile or {}
    domain_key = dyn_challenge.challenge_type if dyn_challenge else "general_domain"
    domain_score = skill_profile.get(domain_key, 1000)
    skill_profile[domain_key] = max(500, domain_score + elo_delta)
    current_user.adaptive_skill_profile = skill_profile

    # Agar dinamik challenge bo'lsa uning holatini saqlash
    if dyn_challenge:
        dyn_challenge.score = feedback.total_score
        dyn_challenge.status = "completed" if feedback.passed else "failed"
        dyn_challenge.completed_at = datetime.now(timezone.utc)

    # 4. Submission obyektini bazaga yozish
    now = datetime.now(timezone.utc)
    submission = Submission(
        user_id=current_user.id,
        simulation_id=simulation_id,
        task_id=task.id if task else None,
        dynamic_challenge_id=dyn_challenge.id if dyn_challenge else None,
        submitted_text=clean_text,
        attachment_path=attachment_path,
        status="passed" if feedback.passed else "revision_needed",
        score=feedback.total_score,
        elo_change=elo_delta,
        xp_earned=xp_earned,
        ai_feedback=feedback.model_dump(),
        reviewed_at=now,
        created_at=now
    )

    db.add(submission)
    db.commit()
    db.refresh(submission)

    # Natijani qaytarish
    res = SubmissionOut.model_validate(submission)
    res.new_elo = new_elo
    res.new_mastery_level = new_mastery_level
    return res

@router.get("/my", response_model=List[SubmissionOut])
def get_my_submissions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    subs = db.query(Submission).filter(Submission.user_id == current_user.id).order_by(Submission.created_at.desc()).all()
    return [SubmissionOut.model_validate(s) for s in subs]

@router.get("/{submission_id}", response_model=SubmissionOut)
def get_submission(submission_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Topshiriq topilmadi")
    # IDOR / BOLA himoyasi: Faqat o'zining topshirig'ini ko'ra oladi
    if sub.user_id != current_user.id and current_user.role not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="Ruxsat berilmagan resurs")
    return SubmissionOut.model_validate(sub)
