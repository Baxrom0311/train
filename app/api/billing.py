from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Transaction
from app.schemas import (
    VIPUpgradeRequest,
    TransactionOut,
    ClickWebhookRequest,
    PaymeWebhookRequest,
    PaymentWebhookResponse
)
from app.api.auth import get_current_user

router = APIRouter(prefix="/billing", tags=["Billing & VIP Monetization"])

def _safe_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

def _normalize_dt(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt

@router.post("/upgrade-vip", response_model=PaymentWebhookResponse)
def upgrade_vip(
    upgrade_data: VIPUpgradeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Talabaning VIP Pro obunasini faollashtirish (Cheksiz AI tahlil, Case Cup ishtiroki va Fast-Track tavsiyanomalar)."""
    days = 365 if upgrade_data.plan_type == "vip_yearly" else 30
    price = upgrade_data.amount or (890000.0 if upgrade_data.plan_type == "vip_yearly" else 99000.0)

    # Foydalanuvchi VIP muddatini hisoblash
    now = _safe_now()
    vip_exp = _normalize_dt(current_user.vip_expires_at)
    current_expires = vip_exp if (vip_exp and vip_exp > now) else now
    new_expires = current_expires + timedelta(days=days)

    current_user.is_vip = True
    current_user.vip_expires_at = new_expires

    # Tranzaksiyani yozish
    tx = Transaction(
        user_id=current_user.id,
        amount=price,
        provider=upgrade_data.provider,
        status="completed",
        plan_type=upgrade_data.plan_type
    )
    db.add(tx)
    db.commit()
    db.refresh(current_user)

    return PaymentWebhookResponse(
        status="success",
        message=f"VIP Pro obunasi muvaffaqiyatli faollashtirildi! Amal qilish muddati: {new_expires.strftime('%Y-%m-%d')}",
        transaction_id=tx.id,
        user_vip_status=current_user.is_vip
    )

@router.post("/click/webhook")
async def click_webhook(
    request: ClickWebhookRequest,
    db: Session = Depends(get_db)
):
    """Click to'lov tizimi rasmiy webhook integratsiyasi."""
    # merchant_trans_id = user_id yoki mavjud transaction_id
    user = db.query(User).filter(User.id == request.merchant_trans_id).first()
    if not user:
        # Email yoki transaction orqali qidirish
        tx = db.query(Transaction).filter(Transaction.id == request.merchant_trans_id).first()
        if tx:
            user = db.query(User).filter(User.id == tx.user_id).first()

    if not user:
        return {"error": -5, "error_note": "Foydalanuvchi topilmadi"}

    # Click Complete (Action = 1)
    if request.action == 1:
        days = 365 if request.amount >= 500000 else 30
        now = _safe_now()
        vip_exp = _normalize_dt(user.vip_expires_at)
        current_expires = vip_exp if (vip_exp and vip_exp > now) else now
        user.is_vip = True
        user.vip_expires_at = current_expires + timedelta(days=days)

        tx = Transaction(
            user_id=user.id,
            amount=request.amount,
            provider="click",
            status="completed",
            plan_type="vip_yearly" if days == 365 else "vip_monthly"
        )
        db.add(tx)
        db.commit()

        return {
            "click_trans_id": request.click_trans_id,
            "merchant_trans_id": request.merchant_trans_id,
            "merchant_confirm_id": tx.id,
            "error": 0,
            "error_note": "Success"
        }

    # Click Prepare (Action = 0)
    return {
        "click_trans_id": request.click_trans_id,
        "merchant_trans_id": request.merchant_trans_id,
        "merchant_prepare_id": user.id,
        "error": 0,
        "error_note": "Success"
    }

@router.post("/payme/webhook")
async def payme_webhook(
    request: PaymeWebhookRequest,
    db: Session = Depends(get_db)
):
    """Payme JSON-RPC to'lov tizimi webhook integratsiyasi."""
    method = request.method
    params = request.params

    if method == "CheckPerformTransaction":
        return {"result": {"allow": True}}

    elif method == "PerformTransaction":
        user_id = params.get("account", {}).get("user_id")
        amount = float(params.get("amount", 9900000)) / 100.0 # tiyin to sum
        
        user = db.query(User).filter(User.id == user_id).first() if user_id else db.query(User).first()
        if user:
            days = 365 if amount >= 500000 else 30
            now = _safe_now()
            vip_exp = _normalize_dt(user.vip_expires_at)
            current_expires = vip_exp if (vip_exp and vip_exp > now) else now
            user.is_vip = True
            user.vip_expires_at = current_expires + timedelta(days=days)

            tx = Transaction(
                user_id=user.id,
                amount=amount,
                provider="payme",
                status="completed",
                plan_type="vip_yearly" if days == 365 else "vip_monthly"
            )
            db.add(tx)
            db.commit()

            return {
                "result": {
                    "transaction": tx.id,
                    "perform_time": int(datetime.now(timezone.utc).timestamp() * 1000),
                    "state": 2
                }
            }
        return {"error": {"code": -31050, "message": {"uz": "Foydalanuvchi topilmadi"}}}

    elif method == "CheckTransaction":
        return {
            "result": {
                "create_time": 1700000000000,
                "perform_time": 1700000000000,
                "cancel_time": 0,
                "transaction": "tx-123",
                "state": 2,
                "reason": None
            }
        }

    return {"result": {"success": True}}

@router.get("/transactions", response_model=List[TransactionOut])
def get_user_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Joriy foydalanuvchining barcha to'lovlari tarixi."""
    return db.query(Transaction).filter(Transaction.user_id == current_user.id).order_by(Transaction.created_at.desc()).all()
