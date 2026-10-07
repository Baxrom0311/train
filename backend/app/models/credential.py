"""
Sertifikat va portfolio (CONTRACT.md §13, Modul 10).

Sertifikat — Run tugagan paytdagi surat: keyin ssenariy yoki ism o'zgarsa
ham ochiq tekshiruvda ko'rinadigan narsa o'zgarmaydi.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Certificate(Base):
    __tablename__ = "certificates"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(12), unique=True, nullable=False)
    run_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)

    # Surat (§13.1)
    holder_name: Mapped[str] = mapped_column(String, nullable=False)
    scenario_title: Mapped[str] = mapped_column(String(200), nullable=False)
    company_name: Mapped[str] = mapped_column(String(120), nullable=False)
    sector: Mapped[str] = mapped_column(String(20), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    competency_scores: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_reason: Mapped[str | None] = mapped_column(String(300), nullable=True)


class Portfolio(Base):
    """Talabaning ochiq sahifasi — default yopiq (opt-in), §13.2."""
    __tablename__ = "portfolios"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    slug: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    headline: Mapped[str] = mapped_column(String(120), nullable=False, default="", server_default="")
    about: Mapped[str] = mapped_column(String(1000), nullable=False, default="", server_default="")
    links: Mapped[list] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)
