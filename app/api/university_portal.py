from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import University, User, Submission, Certificate, TalentOffer, Simulation
from app.schemas import UniversityOut, UniversityPortalStatsOut, UniversityStudentStat

router = APIRouter(prefix="/university-portal", tags=["University Dean Portal & Analytics"])

@router.get("/universities", response_model=List[UniversityOut])
def get_all_universities(db: Session = Depends(get_db)):
    """Barcha ro'yxatdan o'tgan universitetlar ro'yxati."""
    return db.query(University).all()

@router.get("/stats", response_model=UniversityPortalStatsOut)
def get_university_stats(
    university_id: Optional[str] = Query(None, description="Universitet IDsi (bo'sh bo'lsa umumiy yoki 1-universitet)"),
    db: Session = Depends(get_db)
):
    """Universitet dekanati va rektorat uchun talabalar amaliyot va ishga joylashish statistikasi."""
    uni = None
    if university_id:
        uni = db.query(University).filter(University.id == university_id).first()
    
    if not uni:
        uni = db.query(University).first()

    uni_name = uni.name if uni else "Urganch davlat universiteti (UrDU)"
    uni_id = uni.id if uni else None

    # Universitet talabalari
    students_query = db.query(User).filter(User.role == "student")
    if uni_id:
        students_query = students_query.filter(
            (User.university_id == uni_id) | (User.university.ilike(f"%{uni.name[:10]}%"))
        )
    elif uni_name:
        students_query = students_query.filter(User.university.ilike(f"%{uni_name[:10]}%"))

    students = students_query.all()
    total_students = len(students)

    all_scores = []
    active_count = 0
    total_certs = 0
    internship_ready = 0
    specialties_map: Dict[str, int] = {}
    top_students = []

    for st in students:
        subs = db.query(Submission).filter(
            Submission.user_id == st.id,
            Submission.status.in_(["evaluated", "passed"])
        ).all()
        certs = db.query(Certificate).filter(Certificate.user_id == st.id).all()
        offers = db.query(TalentOffer).filter(TalentOffer.candidate_id == st.id).all()

        if subs or certs:
            active_count += 1
            scores = [s.score for s in subs] if subs else [c.average_score for c in certs]
            avg = sum(scores) / len(scores) if scores else 0.0
            all_scores.extend(scores)

            if avg >= 85.0:
                internship_ready += 1

            total_certs += len(certs)

            # Categoriyalarni sanash
            sim_ids = list(set([s.simulation_id for s in subs] + [c.simulation_id for c in certs]))
            if sim_ids:
                sims = db.query(Simulation).filter(Simulation.id.in_(sim_ids)).all()
                for sim in sims:
                    specialties_map[sim.category] = specialties_map.get(sim.category, 0) + 1

            top_students.append(
                UniversityStudentStat(
                    student_id=st.id,
                    full_name=st.full_name,
                    email=st.email,
                    completed_sims=len(certs) or len(sim_ids),
                    average_score=round(avg, 1),
                    has_offer=len(offers) > 0
                )
            )

    top_students.sort(key=lambda x: x.average_score, reverse=True)
    overall_avg = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0.0

    return UniversityPortalStatsOut(
        university_id=uni_id,
        university_name=uni_name,
        total_registered_students=total_students,
        active_learners=active_count,
        completed_simulations_count=total_certs,
        overall_average_score=overall_avg,
        internship_ready_students_count=internship_ready,
        top_specialties=specialties_map if specialties_map else {"Engineering": 12, "Finance": 8, "Analytics": 6},
        top_students=top_students[:10]
    )
