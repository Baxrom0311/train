import os
import uuid
import qrcode
from typing import Optional
from io import BytesIO
from datetime import datetime
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Certificate, Simulation, SimulationTask, Submission
from app.schemas import CertificateOut, CertificateVerifyOut
from app.api.auth import get_current_user
from app.core.security import generate_cert_hmac, verify_cert_hmac
from app.config import settings

router = APIRouter(prefix="/certificates", tags=["Certificates & QR Verification"])

class IssueCertRequest(BaseModel):
    simulation_id: str

@router.post("/issue", response_model=CertificateOut)
def issue_certificate(
    data: Optional[IssueCertRequest] = Body(None),
    simulation_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sim_id = (data.simulation_id if data and data.simulation_id else simulation_id)
    if not sim_id:
        raise HTTPException(status_code=400, detail="simulation_id talab qilinadi")

    sim = db.query(Simulation).filter(Simulation.id == sim_id).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulyatsiya topilmadi")

    # Barcha tasklar topshirilganligini tekshirish
    task_ids = [t.id for t in sim.tasks]
    if not task_ids:
        raise HTTPException(status_code=400, detail="Simulyatsiyada vazifalar mavjud emas")

    user_submissions = db.query(Submission).filter(
        Submission.user_id == current_user.id,
        Submission.task_id.in_(task_ids)
    ).all()

    submitted_task_ids = {s.task_id for s in user_submissions if s.status == "passed"}
    if len(submitted_task_ids) < len(task_ids):
        raise HTTPException(
            status_code=400,
            detail=f"Sertifikat olish uchun barcha topshiriqlarni ({len(task_ids)} ta) muvaffaqiyatli topshirish lozim. Hozirda {len(submitted_task_ids)} ta topshirilgan."
        )

    # O'rtacha ballni hisoblash (aniq 2 xonali qilib yaxlitlash)
    avg_score = round(sum(s.score for s in user_submissions) / len(user_submissions), 2) if user_submissions else 100.0

    # Mavjud sertifikat bor-yo'qligini tekshirish
    existing_cert = db.query(Certificate).filter(
        Certificate.user_id == current_user.id,
        Certificate.simulation_id == sim_id
    ).first()

    if existing_cert:
        return CertificateOut(
            id=existing_cert.id,
            cert_uuid=existing_cert.cert_uuid,
            user_name=current_user.full_name,
            simulation_title=sim.title,
            company_name=sim.company.name if sim.company else "TryJob Platform",
            average_score=existing_cert.average_score,
            issued_at=existing_cert.issued_at,
            hmac_signature=existing_cert.hmac_signature,
            public_verify_url=existing_cert.public_verify_url or f"/verify/{existing_cert.cert_uuid}"
        )

    cert_uuid = f"UZ-TRY-{uuid.uuid4().hex[:8].upper()}"
    signature = generate_cert_hmac(cert_uuid, current_user.id, sim_id, avg_score)
    public_url = f"/verify/{cert_uuid}"

    cert = Certificate(
        cert_uuid=cert_uuid,
        user_id=current_user.id,
        simulation_id=sim_id,
        average_score=avg_score,
        hmac_signature=signature,
        public_verify_url=public_url
    )

    db.add(cert)
    db.commit()
    db.refresh(cert)

    return CertificateOut(
        id=cert.id,
        cert_uuid=cert.cert_uuid,
        user_name=current_user.full_name,
        simulation_title=sim.title,
        company_name=sim.company.name if sim.company else "TryJob Platform",
        average_score=cert.average_score,
        issued_at=cert.issued_at,
        hmac_signature=cert.hmac_signature,
        public_verify_url=public_url
    )

@router.get("/verify/{cert_uuid}", response_model=CertificateVerifyOut)
def verify_certificate(cert_uuid: str, db: Session = Depends(get_db)):
    """Har qanday HR yoki ish beruvchi uchun ochiq (public) sertifikat haqiqiyligini tekshirish"""
    cert = db.query(Certificate).filter(Certificate.cert_uuid == cert_uuid).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Sertifikat topilmadi yoki yaroqsiz")

    # HMAC imzosini tekshirish
    is_genuine = verify_cert_hmac(cert.cert_uuid, cert.user_id, cert.simulation_id, cert.average_score, cert.hmac_signature)

    return CertificateVerifyOut(
        is_valid=is_genuine,
        cert_uuid=cert.cert_uuid,
        student_name=cert.user.full_name if cert.user else "Anonim",
        simulation_title=cert.simulation.title if cert.simulation else "Noma'lum",
        company_name=cert.simulation.company.name if cert.simulation and cert.simulation.company else "TryJob Partner",
        score=cert.average_score,
        issued_at=cert.issued_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
        verification_status="RASMIY TASDIQLANGAN (TryJob Verified Credential)" if is_genuine else "SOXTA / BUZILGAN"
    )

@router.get("/my", response_model=list[CertificateOut])
def get_my_certificates(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    certs = db.query(Certificate).filter(Certificate.user_id == current_user.id).all()
    result = []
    for c in certs:
        result.append(CertificateOut(
            id=c.id,
            cert_uuid=c.cert_uuid,
            user_name=current_user.full_name,
            simulation_title=c.simulation.title if c.simulation else "",
            company_name=c.simulation.company.name if c.simulation and c.simulation.company else "",
            average_score=c.average_score,
            issued_at=c.issued_at,
            hmac_signature=c.hmac_signature,
            public_verify_url=c.public_verify_url or f"/verify/{c.cert_uuid}"
        ))
    return result
