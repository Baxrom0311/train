from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload, selectinload
from app.database import get_db
from app.models import Simulation, CaseCupLeaderboard, User
from app.schemas import SimulationListOut, CaseCupLeaderboardResponse, CaseCupLeaderboardItem

router = APIRouter(prefix="/case-cups", tags=["Case Cups & Championships"])

@router.get("", response_model=List[SimulationListOut])
def get_active_case_cups(db: Session = Depends(get_db)):
    """Faol va e'lon qilingan barcha Case Cup milliy chempionatlar ro'yxati."""
    sims = (
        db.query(Simulation)
        .options(joinedload(Simulation.company), selectinload(Simulation.tasks))
        .filter(
            Simulation.is_case_cup == True,
            Simulation.is_published == True
        )
        .all()
    )
    
    result = []
    for s in sims:
        s_dict = SimulationListOut.model_validate(s)
        s_dict.task_count = len(s.tasks)
        result.append(s_dict)
    return result

@router.get("/{slug}/leaderboard", response_model=CaseCupLeaderboardResponse)
def get_case_cup_leaderboard(slug: str, db: Session = Depends(get_db)):
    """Case Cup chempionati jonli reyting jadvali (Realtime Leaderboard)."""
    sim = db.query(Simulation).filter(Simulation.slug == slug, Simulation.is_published == True).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Case Cup musobaqasi topilmadi")

    entries = (
        db.query(CaseCupLeaderboard)
        .options(joinedload(CaseCupLeaderboard.user).joinedload(User.university_rel))
        .filter(CaseCupLeaderboard.simulation_id == sim.id)
        .order_by(CaseCupLeaderboard.total_score.desc(), CaseCupLeaderboard.submitted_at.asc())
        .all()
    )

    leaderboard_items = []
    for idx, item in enumerate(entries, start=1):
        user = item.user
        university_name = user.university or (user.university_rel.name if user.university_rel else "Noma'lum OTM")
        leaderboard_items.append(
            CaseCupLeaderboardItem(
                rank=idx,
                user_id=item.user_id,
                user_name=user.full_name if user else "Ishtirokchi",
                university=university_name,
                total_score=round(item.total_score, 1),
                submitted_at=item.submitted_at or datetime.now(timezone.utc)
            )
        )

    return CaseCupLeaderboardResponse(
        simulation_id=sim.id,
        simulation_title=sim.title,
        prize_pool=sim.prize_pool,
        deadline=sim.deadline,
        total_participants=len(leaderboard_items),
        leaderboard=leaderboard_items
    )
