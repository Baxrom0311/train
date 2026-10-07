"""
Talent Hunt moduli modellari (CONTRACT.md §5, §6 Modul 4 egaligi).
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, DateTime, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.rbac import GUID


class CandidateVisibility(Base):
    """
    Talaba maxfiyligi — OPT-IN, default YOPIQ (CONTRACT.md §5).
    Yangi student uchun yozuv umuman bo'lmaydi = ko'rinmaydi.
    is_open_to_work=False server_default — SQL darajasida ham yopiq.
    """
    __tablename__ = "candidate_visibility"

    user_id = mapped_column(GUID, ForeignKey("users.id"), primary_key=True)
    is_open_to_work = mapped_column(
        Boolean,
        default=False,
        server_default="false",  # SQL darajasida ham FALSE — bu ENG MUHIM
        nullable=False,
    )
    hidden_from_company_ids = mapped_column(
        JSON,
        default=list,
        server_default="[]",
        nullable=False,
    )
    updated_at = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="visibility")


class TalentOffer(Base):
    """Kompaniyadan talabaga yuborilgan ish taklifi (CONTRACT.md §5)."""
    __tablename__ = "talent_offers"

    id = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    company_id = mapped_column(GUID, ForeignKey("companies.id"), nullable=False)
    candidate_user_id = mapped_column(GUID, ForeignKey("users.id"), nullable=False)
    position_title = mapped_column(String, nullable=False)
    message = mapped_column(String, nullable=False)
    status = mapped_column(
        String,
        nullable=False,
        default="sent",
        server_default="sent",
    )
    # SLA: yuborilgan vaqtdan +5 ish kuni (CONTRACT.md §5)
    respond_due_at = mapped_column(DateTime(timezone=True), nullable=True)
    created_at = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
