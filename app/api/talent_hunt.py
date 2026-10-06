from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func
from app.database import get_db
from app.models import User, Submission, Certificate, Simulation, TalentOffer, Company
from app.schemas import TalentCandidateOut, TalentOfferCreate, TalentOfferOut
from app.api.auth import get_current_user

router = APIRouter(prefix="/talent-hunt", tags=["Talent Hunt (HR Direct Sourcing)"])

@router.get("/candidates", response_model=List[TalentCandidateOut])
def search_top_talents(
    min_score: float = Query(85.0, description="Minimal o'rtacha ball (standart 85%)"),
    university: Optional[str] = Query(None, description="Universitet nomi yoki qidiruv so'zi"),
    category: Optional[str] = Query(None, description="Yo'nalish (Engineering, Finance, Analytics, Legal)"),
    only_vip: bool = Query(False, description="Faqat VIP nomzodlarni ko'rsatish"),
    db: Session = Depends(get_db)
):
    """HR mutaxassislari uchun AI orqali tasdiqlangan iqtidorlarni qidirish va filtrlash."""
    users_query = (
        db.query(User)
        .options(
            joinedload(User.university_rel),
            selectinload(User.submissions).joinedload(Submission.simulation),
            selectinload(User.certificates).joinedload(Certificate.simulation)
        )
        .filter(User.role == "student")
    )

    if university:
        users_query = users_query.filter(User.university.ilike(f"%{university}%"))
    if only_vip:
        users_query = users_query.filter(User.is_vip == True)

    students = users_query.all()
    candidates = []

    for student in students:
        # Talaba topshirgan barcha baholangan submissionlar (keshdan / prefetch)
        subs = [s for s in student.submissions if s.status in ("evaluated", "passed")]
        certs = list(student.certificates)

        if not subs and not certs:
            # Baholanmagan student
            continue

        scores = [s.score for s in subs] if subs else [c.average_score for c in certs]
        avg_score = sum(scores) / len(scores) if scores else 0.0

        if avg_score < min_score:
            continue

        # Yo'nalishlar (categories)
        specialties = list(set(
            [s.simulation.category for s in subs if s.simulation] +
            [c.simulation.category for c in certs if c.simulation]
        ))

        if category and not any(category.lower() in spec.lower() for spec in specialties):
            continue

        latest_sub = max([s.created_at for s in subs], default=student.created_at)
        sim_ids = list(set([s.simulation_id for s in subs] + [c.simulation_id for c in certs]))

        candidates.append(
            TalentCandidateOut(
                user_id=student.id,
                full_name=student.full_name,
                email=student.email,
                university=student.university or (student.university_rel.name if student.university_rel else "OTM"),
                completed_simulations=len(certs) or len(sim_ids),
                average_score=round(avg_score, 1),
                specialties=specialties,
                certificates_count=len(certs),
                is_vip=bool(student.is_vip),
                last_active=latest_sub
            )
        )

    # Ball bo'yicha saralash
    candidates.sort(key=lambda x: x.average_score, reverse=True)
    return candidates

@router.post("/send-offer", response_model=TalentOfferOut)
def send_talent_offer(
    offer_in: TalentOfferCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Nomzodga to'g'ridan-to'g'ri ish / intervyu taklifini (Fast-Track Offer) yuborish."""
    if current_user.role not in ["company_hr", "admin", "superadmin"]:
        raise HTTPException(
            status_code=403,
            detail="Faqat Kompaniya HR yoki Admin nomzodlarga ish taklifi yuborishi mumkin"
        )

    candidate = db.query(User).filter(User.id == offer_in.candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Nomzod topilmadi")

    # Kompaniyani aniqlash (HR foydalanuvchisiga bog'langan kompaniya yoki tanlangan kompaniya)
    company_id = current_user.company_id if current_user.company_id else None
    if not company_id:
        first_comp = db.query(Company).first()
        company_id = first_comp.id if first_comp else None

    if not company_id:
        raise HTTPException(status_code=400, detail="Kompaniya ma'lumoti topilmadi")

    offer = TalentOffer(
        company_id=company_id,
        candidate_id=candidate.id,
        simulation_id=offer_in.simulation_id,
        position_title=offer_in.position_title,
        message=offer_in.message,
        status="sent"
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)

    comp = db.query(Company).filter(Company.id == offer.company_id).first()

    return TalentOfferOut(
        id=offer.id,
        company_id=offer.company_id,
        company_name=comp.name if comp else "Kompaniya",
        candidate_id=candidate.id,
        candidate_name=candidate.full_name,
        simulation_id=offer.simulation_id,
        position_title=offer.position_title,
        message=offer.message,
        status=offer.status,
        created_at=offer.created_at
    )

@router.get("/offers", response_model=List[TalentOfferOut])
def list_talent_offers(
    candidate_id: Optional[str] = Query(None),
    company_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Yuborilgan va qabul qilingan takliflar ro'yxati."""
    query = db.query(TalentOffer)
    if candidate_id:
        query = query.filter(TalentOffer.candidate_id == candidate_id)
    if company_id:
        query = query.filter(TalentOffer.company_id == company_id)

    offers = query.order_by(TalentOffer.created_at.desc()).all()
    result = []
    for off in offers:
        cand = off.candidate
        comp = off.company
        result.append(
            TalentOfferOut(
                id=off.id,
                company_id=off.company_id,
                company_name=comp.name if comp else "Kompaniya",
                candidate_id=off.candidate_id,
                candidate_name=cand.full_name if cand else "Nomzod",
                simulation_id=off.simulation_id,
                position_title=off.position_title,
                message=off.message,
                status=off.status,
                created_at=off.created_at
            )
        )
    return result
