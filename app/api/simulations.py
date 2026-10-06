import re
import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload, selectinload
from app.database import get_db
from app.models import Simulation, SimulationTask, Company, User, DynamicChallenge
from app.schemas import (
    SimulationListOut,
    SimulationDetailOut,
    SimulationCreate,
    SimulationUpdate,
    TaskCreate,
    TaskUpdate,
    TaskOut,
    DynamicChallengeRequest,
    DynamicChallengeOut
)
from app.api.auth import get_current_user
from app.ai.adaptive_engine import adaptive_challenge_engine, LEVEL_DEFINITIONS

router = APIRouter(prefix="/simulations", tags=["Simulations"])

def _slugify(text: str) -> str:
    """O'zbek va inglizcha matnlarni xavfsiz URL slug ga aylantirish"""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text

def _check_simulation_management_permission(user: User, sim: Optional[Simulation] = None, company_id: Optional[str] = None):
    """Kompaniya va Adminlar uchun ruxsat tekshiruvi"""
    if user.role in ["admin", "superadmin"]:
        return True
    if user.role == "company_hr":
        if sim and sim.company_id == user.company_id:
            return True
        if company_id and company_id == user.company_id:
            return True
        if not sim and not company_id and user.company_id:
            return True
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Ushbu simulyatsiyani boshqarish yoki yaratish uchun faqat Kompaniya HR yoki Admin ruxsati talab qilinadi"
    )

@router.get("", response_model=List[SimulationListOut])
def list_simulations(
    category: Optional[str] = Query(None, description="Yo'nalish (Finance, Engineering, Legal, Cybersecurity)"),
    difficulty: Optional[str] = Query(None, description="Qiyinlik darajasi"),
    db: Session = Depends(get_db)
):
    query = (
        db.query(Simulation)
        .options(joinedload(Simulation.company), selectinload(Simulation.tasks))
        .filter(Simulation.is_published == True)
    )
    if category:
        query = query.filter(Simulation.category.ilike(f"%{category}%"))
    if difficulty:
        query = query.filter(Simulation.difficulty.ilike(f"%{difficulty}%"))

    sims = query.all()
    result = []
    for s in sims:
        s_dict = SimulationListOut.model_validate(s)
        s_dict.task_count = len(s.tasks)
        result.append(s_dict)
    return result

@router.post("", response_model=SimulationDetailOut, status_code=status.HTTP_201_CREATED)
def create_simulation(
    data: SimulationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Kompaniyalar va Adminlar uchun yangi Simulyatsiya yaratish API si.
    Kompaniya o'z brendi ostida topshiriqlar platformasiga yangi simulyatsiya qo'shadi.
    """
    # Ruxsat tekshiruvi
    _check_simulation_management_permission(current_user, company_id=data.company_id)

    company_id = data.company_id
    if current_user.role == "company_hr" and current_user.company_id:
        company_id = current_user.company_id
    elif not company_id:
        # Agar admin bo'lsa va company_id ko'rsatilmagan bo'lsa, mavjud 1-kompaniyani olamiz
        first_comp = db.query(Company).first()
        if not first_comp:
            raise HTTPException(status_code=400, detail="Tizimda birorta kompaniya mavjud emas")
        company_id = first_comp.id

    # Kompaniyani tekshirish
    comp = db.query(Company).filter(Company.id == company_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Ko'rsatilgan kompaniya topilmadi")

    # Slug hosil qilish
    if data.slug:
        existing_slug = db.query(Simulation).filter(Simulation.slug == data.slug).first()
        if existing_slug:
            raise HTTPException(status_code=400, detail="Ushbu slug bilan simulyatsiya allaqachon mavjud")
        slug = data.slug
    else:
        slug = _slugify(data.title)
        existing_slug = db.query(Simulation).filter(Simulation.slug == slug).first()
        if existing_slug:
            slug = f"{slug}-{uuid.uuid4().hex[:6]}"

    new_sim = Simulation(
        slug=slug,
        title=data.title,
        company_id=company_id,
        category=data.category,
        difficulty=data.difficulty,
        estimated_hours=data.estimated_hours,
        description=data.description,
        learning_outcomes=data.learning_outcomes or [],
        is_published=data.is_published,
        is_case_cup=data.is_case_cup,
        prize_pool=data.prize_pool,
        deadline=data.deadline
    )

    db.add(new_sim)
    db.commit()
    db.refresh(new_sim)

    return SimulationDetailOut.model_validate(new_sim)

@router.get("/{slug}", response_model=SimulationDetailOut)
def get_simulation_detail(slug: str, db: Session = Depends(get_db)):
    sim = (
        db.query(Simulation)
        .options(joinedload(Simulation.company), selectinload(Simulation.tasks))
        .filter(Simulation.slug == slug, Simulation.is_published == True)
        .first()
    )
    if not sim:
        raise HTTPException(status_code=404, detail="Simulyatsiya topilmadi")
    return SimulationDetailOut.model_validate(sim)

@router.put("/{slug}", response_model=SimulationDetailOut)
def update_simulation(
    slug: str,
    data: SimulationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sim = db.query(Simulation).filter(Simulation.slug == slug).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulyatsiya topilmadi")

    _check_simulation_management_permission(current_user, sim=sim)

    update_dict = data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(sim, key, value)

    db.commit()
    db.refresh(sim)
    return SimulationDetailOut.model_validate(sim)

@router.delete("/{slug}", status_code=status.HTTP_200_OK)
def delete_simulation(
    slug: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sim = db.query(Simulation).filter(Simulation.slug == slug).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulyatsiya topilmadi")

    _check_simulation_management_permission(current_user, sim=sim)

    db.delete(sim)
    db.commit()
    return {"status": "success", "message": f"'{sim.title}' simulyatsiyasi muvaffaqiyatli o'chirildi"}

# ── Topshiriqlar (Simulation Tasks) CRUD ─────────────────────────────────────

@router.post("/{slug}/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_simulation_task(
    slug: str,
    data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Kompaniya HR yoki Admin simulyatsiyaga yangi topshiriq (Task) qo'shishi API si.
    Yo'riqnomalar, rubrikalar va resurs fayllari bilan birga saqlanadi.
    """
    sim = db.query(Simulation).filter(Simulation.slug == slug).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulyatsiya topilmadi")

    _check_simulation_management_permission(current_user, sim=sim)

    # Agar order ko'rsatilmagan yoki 0 bo'lsa, navbatdagi tartib raqami
    if not data.order or data.order <= 0:
        max_order = max([t.order for t in sim.tasks], default=0)
        order = max_order + 1
    else:
        order = data.order

    new_task = SimulationTask(
        simulation_id=sim.id,
        order=order,
        title=data.title,
        briefing_text=data.briefing_text,
        instructions=data.instructions,
        resource_files=data.resource_files or [],
        template_data=data.template_data,
        rubric_criteria=data.rubric_criteria or [
            {"criterion": "Vazifa aniqligi va texnik yechim", "max_score": 50},
            {"criterion": "Xavfsizlik va standartlarga muvofiqlik", "max_score": 50}
        ],
        model_answer=data.model_answer,
        mentor_persona=data.mentor_persona or "lead_engineer"
    )

    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    return TaskOut.model_validate(new_task)

@router.put("/{slug}/tasks/{task_id}", response_model=TaskOut)
def update_simulation_task(
    slug: str,
    task_id: str,
    data: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sim = db.query(Simulation).filter(Simulation.slug == slug).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulyatsiya topilmadi")

    _check_simulation_management_permission(current_user, sim=sim)

    task = db.query(SimulationTask).filter(SimulationTask.id == task_id, SimulationTask.simulation_id == sim.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Topshiriq topilmadi")

    update_dict = data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(task, key, value)

    db.commit()
    db.refresh(task)
    return TaskOut.model_validate(task)

@router.delete("/{slug}/tasks/{task_id}", status_code=status.HTTP_200_OK)
def delete_simulation_task(
    slug: str,
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sim = db.query(Simulation).filter(Simulation.slug == slug).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulyatsiya topilmadi")

    _check_simulation_management_permission(current_user, sim=sim)

    task = db.query(SimulationTask).filter(SimulationTask.id == task_id, SimulationTask.simulation_id == sim.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Topshiriq topilmadi")

    db.delete(task)
    db.commit()
    return {"status": "success", "message": "Topshiriq muvaffaqiyatli o'chirildi"}

# ── Dynamic Infinite Adaptive Challenge Engine ───────────────────────────────

@router.post("/{slug}/dynamic-challenge", response_model=DynamicChallengeOut, status_code=status.HTTP_201_CREATED)
def create_dynamic_adaptive_challenge(
    slug: str,
    req: Optional[DynamicChallengeRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    DYNAMIC INFINITE ADAPTIVE CHALLENGE ENGINE
    Talabaning joriy darajasi (Level 1..N) va oldingi topshirgan yechimlariga qarab,
    unga mos ravishda qiyinlashib boradigan (Edge cases, High-frequency anomalies, Anti-fraud,
    Concurrency, Zero-day bugs) yangi dinamik topshiriq va synthetic dataset generatsiya qiladi.
    Hech qachon tugamaydigan adaptiv amaliyot mexanizmi.
    """
    sim = db.query(Simulation).filter(Simulation.slug == slug).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulyatsiya topilmadi")

    # Adaptiv dvigatel orqali yangi topshiriq yaratish
    challenge = adaptive_challenge_engine.generate_challenge(
        db=db,
        user=current_user,
        simulation=sim,
        req=req
    )

    lvl_meta = LEVEL_DEFINITIONS.get(challenge.level, LEVEL_DEFINITIONS[1])
    target_elo_gain = max(15, int(lvl_meta["xp"] / 10))

    return DynamicChallengeOut(
        id=challenge.id,
        simulation_id=sim.id,
        simulation_title=sim.title,
        company_name=sim.company.name if sim.company else "Tech Enterprise",
        user_id=current_user.id,
        level=challenge.level,
        difficulty_label=challenge.difficulty_label,
        challenge_type=challenge.challenge_type,
        title=challenge.title,
        briefing=challenge.briefing,
        instructions=challenge.instructions,
        synthetic_dataset=challenge.synthetic_dataset,
        starter_code=challenge.starter_code,
        rubric_criteria=challenge.rubric_criteria or [],
        mentor_persona=challenge.mentor_persona,
        status=challenge.status,
        current_elo=current_user.elo_rating or 1000,
        target_elo_gain=target_elo_gain,
        created_at=challenge.created_at
    )

@router.get("/{slug}/dynamic-challenge/active", response_model=Optional[DynamicChallengeOut])
def get_active_dynamic_challenge(
    slug: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sim = db.query(Simulation).filter(Simulation.slug == slug).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulyatsiya topilmadi")

    active_ch = db.query(DynamicChallenge).filter(
        DynamicChallenge.simulation_id == sim.id,
        DynamicChallenge.user_id == current_user.id,
        DynamicChallenge.status == "active"
    ).order_by(DynamicChallenge.created_at.desc()).first()

    if not active_ch:
        return None

    lvl_meta = LEVEL_DEFINITIONS.get(active_ch.level, LEVEL_DEFINITIONS[1])
    target_elo_gain = max(15, int(lvl_meta["xp"] / 10))

    return DynamicChallengeOut(
        id=active_ch.id,
        simulation_id=sim.id,
        simulation_title=sim.title,
        company_name=sim.company.name if sim.company else "Tech Enterprise",
        user_id=current_user.id,
        level=active_ch.level,
        difficulty_label=active_ch.difficulty_label,
        challenge_type=active_ch.challenge_type,
        title=active_ch.title,
        briefing=active_ch.briefing,
        instructions=active_ch.instructions,
        synthetic_dataset=active_ch.synthetic_dataset,
        starter_code=active_ch.starter_code,
        rubric_criteria=active_ch.rubric_criteria or [],
        mentor_persona=active_ch.mentor_persona,
        status=active_ch.status,
        current_elo=current_user.elo_rating or 1000,
        target_elo_gain=target_elo_gain,
        created_at=active_ch.created_at
    )
