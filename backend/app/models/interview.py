"""
AI suhbat mashqi modellari (CONTRACT.md §24.1, §6 Modul 14 egaligi).

Suhbat vakansiyadan boshlanadi, lekin lavozim/kompaniya/talablar nusxa
sifatida saqlanadi — vakansiya keyin o'zgarsa yoki o'chsa ham natija o'qiladi.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column

from app.database import Base
from app.models.enums import InterviewMessageKind, InterviewRole, InterviewStatus, Sector
from app.models.rbac import GUID


def _str_enum(enum_cls, name: str, length: int = 20):
    """VARCHAR + CHECK (Postgres native enum emas)."""
    return SAEnum(enum_cls, native_enum=False, values_callable=lambda e: [m.value for m in e], length=length,
                  create_constraint=True, name=name)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Interview(Base):
    """Bitta sinov suhbati: savollar rejasi, holat va baholash natijasi (§24.1)."""
    __tablename__ = "interviews"
    __table_args__ = (
        Index("ix_interviews_user_created", "user_id", "created_at"),
        # bir talabada bir vaqtda bitta faol suhbat
        Index("uq_interviews_one_active", "user_id", unique=True, postgresql_where=text("status = 'active'")),
    )

    id = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    vacancy_id = mapped_column(GUID, ForeignKey("vacancies.id", ondelete="SET NULL"), nullable=True)
    position = mapped_column(String(120), nullable=False)
    company_name = mapped_column(String(255), nullable=False)
    sector = mapped_column(_str_enum(Sector, "ck_interviews_sector"), nullable=False)
    requirements = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    focus = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    lang = mapped_column(String(2), nullable=False, default="uz")
    # [{competency, text}] — asosiy savollar
    plan = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    current = mapped_column(Integer, nullable=False, default=0)
    follow_ups = mapped_column(Integer, nullable=False, default=0)
    status = mapped_column(_str_enum(InterviewStatus, "ck_interviews_status"), nullable=False,
                           default=InterviewStatus.ACTIVE)
    score = mapped_column(Numeric(4, 1), nullable=True)
    competency_scores = mapped_column(JSONB, nullable=True)
    feedback = mapped_column(JSONB, nullable=True)
    tokens_used = mapped_column(Integer, nullable=False, default=0)
    eval_attempts = mapped_column(Integer, nullable=False, default=0)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    finished_at = mapped_column(DateTime(timezone=True), nullable=True)
    evaluated_at = mapped_column(DateTime(timezone=True), nullable=True)


class InterviewMessage(Base):
    """Suhbatdagi bitta xabar: suhbatdosh savoli yoki talaba javobi (§24.1)."""
    __tablename__ = "interview_messages"
    __table_args__ = (UniqueConstraint("interview_id", "seq", name="uq_interview_messages_seq"),)

    id = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    interview_id = mapped_column(GUID, ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False)
    seq = mapped_column(Integer, nullable=False)
    role = mapped_column(_str_enum(InterviewRole, "ck_interview_messages_role"), nullable=False)
    kind = mapped_column(_str_enum(InterviewMessageKind, "ck_interview_messages_kind"), nullable=False)
    question_index = mapped_column(Integer, nullable=False)
    body = mapped_column(Text, nullable=False)
    generated = mapped_column(Boolean, nullable=False, default=False)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
