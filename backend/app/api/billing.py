from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime, UTC
import uuid

from app.database import get_db
from app.core.deps import require_permission
from app.models.user import User
from app.models.billing import Invoice, Company, University

router = APIRouter(prefix="/api/v1/admin/invoices", tags=["admin_invoices"])

class InvoiceCreate(BaseModel):
    payer_type: Literal["company", "university"]
    payer_id: uuid.UUID
    amount: float
    currency: str = "UZS"
    notes: Optional[str] = None

class InvoiceOut(BaseModel):
    id: uuid.UUID
    payer_type: str
    payer_id: uuid.UUID
    amount: float
    currency: str
    status: str
    issued_by_admin_id: uuid.UUID
    paid_marked_at: datetime | None = None
    notes: str | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

@router.post("", response_model=InvoiceOut)
async def create_invoice(
    data: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("manage_billing"))
):
    model = Company if data.payer_type == "company" else University
    stmt = select(model).where(model.id == data.payer_id)
    result = await db.execute(stmt)
    org = result.scalars().first()
    
    if not org:
        raise HTTPException(status_code=404, detail="Payer organization not found")
        
    invoice = Invoice(
        payer_type=data.payer_type,
        payer_id=data.payer_id,
        amount=data.amount,
        currency=data.currency,
        notes=data.notes,
        issued_by_admin_id=user.id
    )
    db.add(invoice)
    await db.commit()
    await db.refresh(invoice)
    return invoice

@router.get("", response_model=List[InvoiceOut])
async def list_invoices(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("manage_billing"))
):
    stmt = select(Invoice)
    result = await db.execute(stmt)
    return list(result.scalars().all())

@router.get("/{invoice_id}", response_model=InvoiceOut)
async def get_invoice(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("manage_billing"))
):
    stmt = select(Invoice).where(Invoice.id == invoice_id)
    result = await db.execute(stmt)
    invoice = result.scalars().first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    return invoice

@router.post("/{invoice_id}/mark-paid", response_model=InvoiceOut)
async def mark_invoice_paid(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("manage_billing"))
):
    stmt = select(Invoice).where(Invoice.id == invoice_id)
    result = await db.execute(stmt)
    invoice = result.scalars().first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    if invoice.status == "paid":
        return invoice
        
    invoice.status = "paid"
    invoice.paid_marked_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(invoice)
    return invoice
