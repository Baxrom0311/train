from sqlalchemy import String, Float, Numeric, Boolean, DateTime, ForeignKey, Text, CheckConstraint, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, UTC
from decimal import Decimal
import uuid

from app.database import Base
from app.models.enums import OrgType, InvoiceStatus

class Company(Base):
    __tablename__ = "companies"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    industry: Mapped[str] = mapped_column(String)
    contact_email: Mapped[str] = mapped_column(String)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class University(Base):
    __tablename__ = "universities"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    city: Mapped[str] = mapped_column(String)
    contact_email: Mapped[str] = mapped_column(String)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        # Pul miqdori manfiy yoki nol bo'lishi mumkin emas edi avvalgi
        # versiyada (sinab tasdiqlangan haqiqiy bug) — endi DB darajasida
        # ham qattiq cheklangan.
        CheckConstraint("amount > 0", name="ck_invoices_amount_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    payer_type: Mapped[OrgType] = mapped_column(
        SAEnum(OrgType, native_enum=False, values_callable=lambda e: [m.value for m in e])
    )
    payer_id: Mapped[uuid.UUID] = mapped_column() # UUID for Company or University
    # Numeric — pul miqdorlari uchun Float ishlatish yaxlitlash xatolariga
    # olib kelishi mumkin (haqiqiy moliyaviy ma'lumot uchun mos emas).
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String, default="UZS")
    status: Mapped[InvoiceStatus] = mapped_column(
        SAEnum(InvoiceStatus, native_enum=False, values_callable=lambda e: [m.value for m in e]),
        default=InvoiceStatus.PENDING,
    )
    issued_by_admin_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    paid_marked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
