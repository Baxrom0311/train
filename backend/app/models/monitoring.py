"""
Xato guruhlari (CONTRACT.md §32.3, Modul 1).

Bir xil xato (fingerprint) — bitta qator: hisob, birinchi/oxirgi marta va
oxirgi hodisaning traceback'i. So'rov tanasi, sarlavhalar va foydalanuvchi
saqlanmaydi.
"""
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

SOURCES = ("api", "worker", "frontend")
STATUSES = ("open", "resolved")


class ErrorGroup(Base):
    __tablename__ = "error_groups"
    __table_args__ = (
        CheckConstraint("source IN ('api', 'worker', 'frontend')", name="ck_error_groups_source"),
        CheckConstraint("status IN ('open', 'resolved')", name="ck_error_groups_status"),
        Index("ix_error_groups_status_last_seen", "status", "last_seen"),
        # §32.3: soatiga yangi guruhlar chegarasi
        Index("ix_error_groups_source_first_seen", "source", "first_seen"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    level: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    location: Mapped[str] = mapped_column(String(300), nullable=False, server_default=text("''"))
    detail: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_request_id: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'open'"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
