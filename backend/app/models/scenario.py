"""
Ssenariy dvigateli jadvallari (CONTRACT.md §9.7). Barcha vaqtlar UTC
`timestamptz`; Toshkent vaqti faqat `app/scenario/clock.py`da hisoblanadi.
"""
import uuid
from datetime import date as date_type, datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import (
    ChatContentType,
    ChatSender,
    HolidaySource,
    RunEventStatus,
    RunStatus,
    ScenarioVersionStatus,
    Sector,
)

# §9.0 Q12 — gemini-embedding-001, 768 o'lcham. O'zgarsa: migratsiya + qayta indekslash.
EMBEDDING_DIM = 768


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _enum(e):
    return SAEnum(e, native_enum=False, values_callable=lambda x: [m.value for m in x])


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class Scenario(Base):
    __tablename__ = "scenarios"

    id: Mapped[uuid.UUID] = _uuid_pk()
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    sector: Mapped[Sector] = mapped_column(_enum(Sector), nullable=False)
    company_name: Mapped[str] = mapped_column(String(120), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    versions = relationship("ScenarioVersion", back_populates="scenario", cascade="all, delete-orphan")


class ScenarioVersion(Base):
    __tablename__ = "scenario_versions"
    __table_args__ = (UniqueConstraint("scenario_id", "version", name="uq_scenario_versions_version"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    scenario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ScenarioVersionStatus] = mapped_column(
        _enum(ScenarioVersionStatus), nullable=False, default=ScenarioVersionStatus.DRAFT
    )
    # app.scenario.schema.ScenarioDefinition.model_dump(mode="json", by_alias=True)
    definition: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    scenario = relationship("Scenario", back_populates="versions")
    documents = relationship("ScenarioDocument", back_populates="version", cascade="all, delete-orphan")


class ScenarioDocument(Base):
    """RAG manbasi (§9.4). Rubrika/namunaviy javob/hint bu yerga HECH QACHON yozilmaydi."""
    __tablename__ = "scenario_documents"
    __table_args__ = (UniqueConstraint("scenario_version_id", "key", name="uq_scenario_documents_key"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    scenario_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scenario_versions.id", ondelete="CASCADE"), nullable=False
    )
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Persona.knows dan hisoblanadi — qidiruv filtri
    visible_to_personas: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    version = relationship("ScenarioVersion", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_document_chunks_index"),
        Index("ix_document_chunks_tsv", "tsv", postgresql_using="gin"),
        Index(
            "ix_document_chunks_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scenario_documents.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # Embedding API ishlamasa NULL qoladi — qidiruv full-text'ga tushadi (§9.4)
    embedding = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(80), nullable=True)
    # 'simple' — o'zbek tili uchun Postgres stemmer'i yo'q
    tsv = mapped_column(TSVECTOR, Computed("to_tsvector('simple', text)", persisted=True))

    document = relationship("ScenarioDocument", back_populates="chunks")


class Run(Base):
    __tablename__ = "runs"
    __table_args__ = (
        Index("ix_runs_status_ends_at", "status", "ends_at"),
        Index("ix_runs_user_id", "user_id"),
        # Bir ssenariy versiyasida bir vaqtda bitta faol Run (§9.7)
        Index(
            "uq_runs_one_open_per_version",
            "user_id",
            "scenario_version_id",
            unique=True,
            postgresql_where=text("status IN ('scheduled', 'active')"),
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    scenario_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("scenario_versions.id"), nullable=False)
    status: Mapped[RunStatus] = mapped_column(_enum(RunStatus), nullable=False, default=RunStatus.SCHEDULED)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    flags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    ai_tokens_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    competency_scores: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    final_report: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    scenario_version = relationship("ScenarioVersion")
    events = relationship("RunEvent", back_populates="run", cascade="all, delete-orphan")


class RunEvent(Base):
    __tablename__ = "run_events"
    __table_args__ = (
        UniqueConstraint("run_id", "node_id", name="uq_run_events_node"),
        Index("ix_run_events_status_scheduled_at", "status", "scheduled_at"),
        Index("ix_run_events_status_due_at", "status", "due_at"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    node_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[RunEventStatus] = mapped_column(
        _enum(RunEventStatus), nullable=False, default=RunEventStatus.PENDING
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    first_opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    choice: Mapped[str | None] = mapped_column(String(64), nullable=True)
    hints_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    run = relationship("Run", back_populates="events")


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id: Mapped[uuid.UUID] = _uuid_pk()
    owner_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("runs.id", ondelete="SET NULL"), nullable=True)
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# Mentorning o'zi boshlagan xabarlari (§9.13)
CHAT_PURPOSE_REVIEW = "review"
CHAT_PURPOSE_NUDGE = "nudge"


class ChatMessage(Base):
    """Faqat Run ichidagi personaj chati (§9.5) — TalentOffer xabarlari bilan aralashmaydi."""
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_chat_messages_thread", "run_id", "persona_key", "created_at"),
        CheckConstraint("purpose IN ('review', 'nudge')", name="ck_chat_messages_purpose"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    persona_key: Mapped[str] = mapped_column(String(64), nullable=False)
    sender: Mapped[ChatSender] = mapped_column(_enum(ChatSender), nullable=False)
    content_type: Mapped[ChatContentType] = mapped_column(
        _enum(ChatContentType), nullable=False, default=ChatContentType.TEXT
    )
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    file_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("uploaded_files.id"), nullable=True)
    link_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    # CHAT_PURPOSE_*; oddiy suhbatda NULL
    purpose: Mapped[str | None] = mapped_column(String(16), nullable=True)
    node_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # bitta urinishga bitta izoh — baholash job'i qayta ishlasa takrorlanmaydi
    submission_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("submissions.id", ondelete="CASCADE"), nullable=True, unique=True
    )


class WorkHoliday(Base):
    """§9.2 — ish kuni bo'lmagan sanalar. `manual` yozuvini avtomatik sinxronizatsiya o'zgartirmaydi."""
    __tablename__ = "work_holidays"

    date: Mapped[date_type] = mapped_column(Date, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source: Mapped[HolidaySource] = mapped_column(
        _enum(HolidaySource), nullable=False, default=HolidaySource.AUTO
    )
