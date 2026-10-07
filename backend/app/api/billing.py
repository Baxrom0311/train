"""
B2B invoice'lar — faqat admin qo'lda boshqaradi, Click/Payme yo'q (CONTRACT.md §7, §11.3).
Modul 3 egaligi: backend/app/api/billing.py
"""
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_permission
from app.database import get_db
from app.models.billing import Company, Invoice, University
from app.models.enums import InvoiceStatus, OrgType
from app.models.user import User

router = APIRouter(prefix="/api/v1/admin/invoices", tags=["admin_invoices"])
# Tashkilot xodimi o'z invoice'larini ko'radi
org_router = APIRouter(prefix="/api/v1/billing", tags=["billing"])

ORG_MODELS = {OrgType.COMPANY: Company, OrgType.UNIVERSITY: University}


class InvoiceCreate(BaseModel):
    payer_type: OrgType
    payer_id: uuid.UUID
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    currency: Literal["UZS", "USD"] = "UZS"
    notes: str | None = Field(default=None, max_length=1000)


class InvoiceOut(BaseModel):
    id: uuid.UUID
    payer_type: OrgType
    payer_id: uuid.UUID
    amount: Decimal
    currency: str
    status: InvoiceStatus
    issued_by_admin_id: uuid.UUID
    paid_marked_at: datetime | None = None
    notes: str | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class InvoiceWithPayer(InvoiceOut):
    payer_name: str | None


async def _payer_names(db: AsyncSession, invoices: list[Invoice]) -> dict[uuid.UUID, str]:
    names: dict[uuid.UUID, str] = {}
    for org_type, model in ORG_MODELS.items():
        ids = {i.payer_id for i in invoices if i.payer_type == org_type}
        if ids:
            names.update((row.id, row.name) for row in await db.execute(select(model.id, model.name).where(model.id.in_(ids))))
    return names


async def _with_payers(db: AsyncSession, invoices: list[Invoice]) -> list[InvoiceWithPayer]:
    names = await _payer_names(db, invoices)
    return [
        InvoiceWithPayer(**InvoiceOut.model_validate(i).model_dump(), payer_name=names.get(i.payer_id))
        for i in invoices
    ]


async def _invoice(db: AsyncSession, invoice_id: uuid.UUID) -> Invoice:
    invoice = (await db.execute(
        select(Invoice).where(Invoice.id == invoice_id).with_for_update()
    )).scalars().first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.post("", response_model=InvoiceWithPayer, status_code=201)
async def create_invoice(
    data: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("manage_billing")),
):
    model = ORG_MODELS[data.payer_type]
    org = await db.get(model, data.payer_id)
    if not org:
        raise HTTPException(status_code=404, detail="Payer organization not found")
    if not org.is_verified:
        # tasdiqlanmagan tashkilotga invoice yozilmaydi (docs/tasks/03 §3)
        raise HTTPException(status_code=400, detail="Payer organization is not verified")

    invoice = Invoice(
        payer_type=data.payer_type,
        payer_id=data.payer_id,
        amount=data.amount,
        currency=data.currency,
        notes=(data.notes or "").strip() or None,
        issued_by_admin_id=user.id,
    )
    db.add(invoice)
    await db.commit()
    await db.refresh(invoice)
    return (await _with_payers(db, [invoice]))[0]


@router.get("", response_model=list[InvoiceWithPayer])
async def list_invoices(
    status: InvoiceStatus | None = None,
    payer_type: OrgType | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("manage_billing")),
):
    q = select(Invoice).order_by(Invoice.created_at.desc())
    if status:
        q = q.where(Invoice.status == status)
    if payer_type:
        q = q.where(Invoice.payer_type == payer_type)
    return await _with_payers(db, list((await db.execute(q)).scalars()))


@router.get("/{invoice_id}", response_model=InvoiceWithPayer)
async def get_invoice(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("manage_billing")),
):
    invoice = await db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return (await _with_payers(db, [invoice]))[0]


@router.post("/{invoice_id}/mark-paid", response_model=InvoiceWithPayer)
async def mark_invoice_paid(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("manage_billing")),
):
    invoice = await _invoice(db, invoice_id)
    if invoice.status == InvoiceStatus.CANCELLED:
        raise HTTPException(status_code=409, detail="Cancelled invoice cannot be paid")
    if invoice.status == InvoiceStatus.PENDING:
        invoice.status = InvoiceStatus.PAID
        invoice.paid_marked_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(invoice)
    return (await _with_payers(db, [invoice]))[0]


@router.post("/{invoice_id}/cancel", response_model=InvoiceWithPayer)
async def cancel_invoice(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("manage_billing")),
):
    invoice = await _invoice(db, invoice_id)
    if invoice.status == InvoiceStatus.PAID:
        raise HTTPException(status_code=409, detail="Paid invoice cannot be cancelled")
    if invoice.status == InvoiceStatus.PENDING:
        invoice.status = InvoiceStatus.CANCELLED
        await db.commit()
        await db.refresh(invoice)
    return (await _with_payers(db, [invoice]))[0]


@org_router.get("/invoices", response_model=list[InvoiceWithPayer])
async def my_org_invoices(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("view_org_invoices")),
):
    """Faqat o'z tashkilotining invoice'lari (§11.3)."""
    if user.org_type is None or user.org_id is None:
        return []
    invoices = (await db.execute(
        select(Invoice)
        .where(Invoice.payer_type == user.org_type, Invoice.payer_id == user.org_id)
        .order_by(Invoice.created_at.desc())
    )).scalars()
    return await _with_payers(db, list(invoices))
