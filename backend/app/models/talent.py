"""
Talent Hunt moduli modellari (CONTRACT.md §5, §6 Modul 4 egaligi).
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Index, Integer, JSON, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.rbac import GUID
from app.models.enums import (
    ApplicationInterviewFormat, ApplicationInterviewOutcome, ApplicationInterviewStatus, ApplicationStatus,
    AssessmentStatus, Employment, OfferResponse, Sector, TalentOfferStatus, VacancyStatus, WorkFormat,
)


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
    __table_args__ = (
        # Bir kompaniya — bir nomzod: javob kutilayotgan taklif bittadan oshmaydi (§10.2)
        Index(
            "uq_talent_offers_open_pair",
            "company_id",
            "candidate_user_id",
            unique=True,
            postgresql_where=text("status IN ('sent', 'viewed')"),
        ),
    )

    id = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    company_id = mapped_column(GUID, ForeignKey("companies.id"), nullable=False)
    candidate_user_id = mapped_column(GUID, ForeignKey("users.id"), nullable=False)
    position_title = mapped_column(String, nullable=False)
    message = mapped_column(String, nullable=False)
    status = mapped_column(
        SAEnum(TalentOfferStatus, native_enum=False, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=TalentOfferStatus.SENT,
        server_default="sent",
    )
    # SLA: yuborilgan vaqtdan +5 ish kuni (CONTRACT.md §10.2)
    respond_due_at = mapped_column(DateTime(timezone=True), nullable=True)
    # Talaba javobi (CONTRACT.md §10.2); kontakt faqat accepted'da ochiladi
    response = mapped_column(
        SAEnum(OfferResponse, native_enum=False, values_callable=lambda e: [m.value for m in e], length=20,
               create_constraint=True, name="ck_talent_offers_response"),
        nullable=True,
    )
    response_note = mapped_column(String(500), nullable=True)
    responded_at = mapped_column(DateTime(timezone=True), nullable=True)
    # qaysi vakansiyadan (§23.3); vakansiya o'chsa taklif qoladi
    vacancy_id = mapped_column(GUID, ForeignKey("vacancies.id", ondelete="SET NULL"), nullable=True)
    created_at = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


def _str_enum(enum_cls, name: str, length: int = 20):
    """Postgres native enum emas — VARCHAR + CHECK (yangi qiymat migratsiyasi oson)."""
    return SAEnum(enum_cls, native_enum=False, values_callable=lambda e: [m.value for m in e], length=length,
                  create_constraint=True, name=name)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Vacancy(Base):
    """Kompaniya vakansiyasi va uning talablari (CONTRACT.md §23.1)."""
    __tablename__ = "vacancies"
    __table_args__ = (Index("ix_vacancies_company_status", "company_id", "status"),)

    id = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    company_id = mapped_column(GUID, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    created_by = mapped_column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    title = mapped_column(String(120), nullable=False)
    description = mapped_column(String(4000), nullable=False)
    sector = mapped_column(_str_enum(Sector, "ck_vacancies_sector"), nullable=False)
    employment = mapped_column(_str_enum(Employment, "ck_vacancies_employment"), nullable=False)
    work_format = mapped_column(_str_enum(WorkFormat, "ck_vacancies_work_format"), nullable=False)
    location = mapped_column(String(120), nullable=True)
    salary_min = mapped_column(Integer, nullable=True)
    salary_max = mapped_column(Integer, nullable=True)
    # {competency: min_score} — §9.6 kompetensiyalari, 0–100
    requirements = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    min_score = mapped_column(Integer, nullable=True)
    # shu ishga yaqin ssenariylar (str uuid), talabaga "mashq qiling"
    scenario_ids = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    status = mapped_column(_str_enum(VacancyStatus, "ck_vacancies_status"), nullable=False, default=VacancyStatus.DRAFT)
    published_at = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at = mapped_column(DateTime(timezone=True), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)


class VacancyApplication(Base):
    """Talabaning vakansiyaga arizasi — profilini shu kompaniyaga ko'rsatishga rozilik (§23.3)."""
    __tablename__ = "vacancy_applications"
    __table_args__ = (
        UniqueConstraint("vacancy_id", "user_id", name="uq_vacancy_applications_pair"),
        Index("ix_vacancy_applications_user", "user_id"),
    )

    id = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    vacancy_id = mapped_column(GUID, ForeignKey("vacancies.id", ondelete="CASCADE"), nullable=False)
    user_id = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    note = mapped_column(String(1000), nullable=True)
    status = mapped_column(_str_enum(ApplicationStatus, "ck_vacancy_applications_status"), nullable=False,
                           default=ApplicationStatus.APPLIED)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)


class ApplicationInterview(Base):
    """Kompaniya arizachiga taklif qilgan haqiqiy suhbat (CONTRACT.md §25.1)."""
    __tablename__ = "application_interviews"
    __table_args__ = (
        # bir arizada bitta faol suhbat (§25.1)
        Index(
            "uq_application_interviews_active",
            "application_id",
            unique=True,
            postgresql_where=text("status IN ('proposed', 'confirmed')"),
        ),
        Index("ix_application_interviews_status_starts", "status", "starts_at"),
    )

    id = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    application_id = mapped_column(GUID, ForeignKey("vacancy_applications.id", ondelete="CASCADE"), nullable=False,
                                   index=True)
    created_by = mapped_column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    round = mapped_column(Integer, nullable=False, default=1)
    # ISO (UTC) qatorlar, o'sish tartibida, 1–3 ta
    slots = mapped_column(JSONB, nullable=False)
    duration_minutes = mapped_column(Integer, nullable=False)
    format = mapped_column(_str_enum(ApplicationInterviewFormat, "ck_application_interviews_format"), nullable=False)
    place = mapped_column(String(300), nullable=False)
    note = mapped_column(String(1000), nullable=True)
    status = mapped_column(_str_enum(ApplicationInterviewStatus, "ck_application_interviews_status"), nullable=False,
                           default=ApplicationInterviewStatus.PROPOSED)
    starts_at = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_at = mapped_column(DateTime(timezone=True), nullable=True)
    decline_reason = mapped_column(String(500), nullable=True)
    outcome = mapped_column(_str_enum(ApplicationInterviewOutcome, "ck_application_interviews_outcome"), nullable=True)
    outcome_note = mapped_column(String(1000), nullable=True)   # faqat kompaniyaga
    reminded_at = mapped_column(DateTime(timezone=True), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)


class ApplicationAssessment(Base):
    """Arizachiga yuborilgan sinov topshirig'i — kompaniya ssenariysi bo'yicha Run (CONTRACT.md §26.1)."""
    __tablename__ = "application_assessments"
    __table_args__ = (
        # bir arizada bitta kutayotgan topshiriq
        Index(
            "uq_application_assessments_assigned",
            "application_id",
            unique=True,
            postgresql_where=text("status = 'assigned'"),
        ),
    )

    id = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    application_id = mapped_column(GUID, ForeignKey("vacancy_applications.id", ondelete="CASCADE"), nullable=False,
                                   index=True)
    scenario_id = mapped_column(GUID, ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False)
    # yuborilgan paytdagi nashr versiyasi — keyingi tahrirlar talabaning sinoviga ta'sir qilmaydi
    scenario_version_id = mapped_column(GUID, ForeignKey("scenario_versions.id", ondelete="CASCADE"), nullable=False)
    run_id = mapped_column(GUID, ForeignKey("runs.id", ondelete="SET NULL"), nullable=True, unique=True)
    note = mapped_column(String(1000), nullable=True)
    start_by = mapped_column(DateTime(timezone=True), nullable=False)
    status = mapped_column(_str_enum(AssessmentStatus, "ck_application_assessments_status"), nullable=False,
                           default=AssessmentStatus.ASSIGNED)
    created_by = mapped_column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    started_at = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)
