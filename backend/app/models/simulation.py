import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    String, Boolean, DateTime, ForeignKey, Text, Float, Integer, SmallInteger, JSON,
    CheckConstraint, Index, Enum as SAEnum, text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.database import Base
from app.models.enums import Sector, AIEvalStatus

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

class Simulation(Base):
    __tablename__ = "simulations"
    
    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    sector: Mapped[Sector] = mapped_column(
        SAEnum(Sector, native_enum=False, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    difficulty: Mapped[str] = mapped_column(String, nullable=False)
    company_name: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    tasks = relationship("SimulationTask", back_populates="simulation", cascade="all, delete-orphan", lazy="selectin")

class SimulationTask(Base):
    __tablename__ = "simulation_tasks"
    
    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("simulations.id"), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    expected_skills: Mapped[list | dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    simulation = relationship("Simulation", back_populates="tasks")
    submissions = relationship("Submission", back_populates="task", cascade="all, delete-orphan")

class Submission(Base):
    """
    Umumiy javob jadvali (CONTRACT.md §9.7): eski simulyatsiya task'i
    (`task_id`, LEGACY) YOKI Run hodisasi (`run_event_id`) — aynan bittasi.
    """
    __tablename__ = "submissions"
    __table_args__ = (
        CheckConstraint("(task_id IS NULL) <> (run_event_id IS NULL)", name="ck_submissions_target"),
        Index(
            "uq_submissions_run_event_attempt",
            "run_event_id",
            "attempt",
            unique=True,
            postgresql_where=text("run_event_id IS NOT NULL"),
        ),
        Index("ix_submissions_run_id", "run_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("simulation_tasks.id"), nullable=True)
    run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), nullable=True)
    run_event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("run_events.id", ondelete="CASCADE"), nullable=True
    )
    attempt: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1, server_default=text("1"))
    late: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    rubric_scores: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    file_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("uploaded_files.id"), nullable=True)
    link_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # §19.4: `code` javobi alohida (yashirin testlar uchun) va testlar natijasi
    code: Mapped[str | None] = mapped_column(Text, nullable=True)
    check_results: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ai_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_eval_status: Mapped[AIEvalStatus] = mapped_column(
        SAEnum(AIEvalStatus, native_enum=False, values_callable=lambda e: [m.value for m in e]),
        default=AIEvalStatus.COMPLETED,
    )
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    task = relationship("SimulationTask", back_populates="submissions")
