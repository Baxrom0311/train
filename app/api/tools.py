from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from app.core.sandbox import SafePythonSandbox
from app.ai.interview import AIInterviewEngine, INTERVIEW_QUESTIONS
from app.api.auth import get_current_user
from app.models import User

router = APIRouter(prefix="/tools", tags=["AI Interactive Tools & Sandbox"])

class PythonRunRequest(BaseModel):
    code: str = Field(..., max_length=10000)
    timeout_seconds: Optional[float] = 5.0

class InterviewAnswerRequest(BaseModel):
    category: Optional[str] = "finance"
    simulation_slug: Optional[str] = None
    question: str
    answer: Optional[str] = None
    student_answer: Optional[str] = None
    mentor_persona: Optional[str] = "lead_engineer"

class DocumentAuditRequest(BaseModel):
    doc_type: str = "ehf" # ehf (Elektron hisob-faktura), contract, loan_app
    tin: Optional[str] = None # STIR / INN
    company_name: Optional[str] = None
    items_total: float = 0.0
    vat_rate: float = 0.12 # QQS 12%
    declared_total: float = 0.0

@router.post("/run-python")
@router.post("/sandbox")
def run_python_code(data: PythonRunRequest):
    """Xavfsiz Python Sandbox muhitida kodni ishlatish"""
    res = SafePythonSandbox.execute_code(data.code, timeout_sec=data.timeout_seconds or 5.0)
    return res

@router.get("/interview-questions")
def get_interview_questions(category: str = "finance"):
    """Yo'nalish bo'yicha suhbat savollarini olish"""
    questions = INTERVIEW_QUESTIONS.get(category.lower(), INTERVIEW_QUESTIONS["finance"])
    return {"category": category, "questions": questions}

@router.post("/mock-interview")
def evaluate_interview(data: InterviewAnswerRequest):
    """Talaba intervyu javobini STARR bo'yicha tahlil qilish"""
    ans = data.student_answer or data.answer or ""
    return AIInterviewEngine.evaluate_interview_answer(
        category=data.category or "finance",
        question=data.question,
        user_answer=ans,
        mentor_persona_key=data.mentor_persona or "lead_engineer"
    )

@router.post("/document-audit")
def audit_business_document(data: DocumentAuditRequest):
    """
    O'zbekiston Didox / Elektron Hisob-faktura va shartnoma tekshiruvi.
    """
    errors = []
    warnings = []

    # 1. STIR (INN) tekshiruvi: 9 ta raqam bo'lishi shart
    if data.tin:
        if not (len(data.tin) == 9 and data.tin.isdigit()):
            errors.append(f"STIR (INN) noto'g'ri kiritilgan: '{data.tin}'. O'zbekiston standartida STIR aynan 9 ta raqamdan iborat bo'lishi shart.")

    # 2. QQS (12%) hisob-kitob tekshiruvi
    expected_vat = round(data.items_total * data.vat_rate, 2)
    expected_total = round(data.items_total + expected_vat, 2)

    if data.declared_total > 0 and abs(data.declared_total - expected_total) > 1.0:
        errors.append(
            f"Hisob-faktura jami summasida nomuvofiqlik: Kiritilgan: {data.declared_total:,.2f} so'm, "
            f"Kutilgan (QQS 12% bilan): {expected_total:,.2f} so'm (QQS: {expected_vat:,.2f} so'm)."
        )

    is_valid = len(errors) == 0

    return {
        "is_valid": is_valid,
        "doc_type": data.doc_type,
        "errors": errors,
        "warnings": warnings,
        "calculated_vat_12": expected_vat,
        "calculated_grand_total": expected_total,
        "status": "HUJJAT TASDIQLANDI (VALID)" if is_valid else "XATOLIKLAR MAVJUD (INVALID)"
    }
