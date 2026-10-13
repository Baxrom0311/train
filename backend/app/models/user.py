import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, Index, Enum as SAEnum, CheckConstraint
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.rbac import GUID
from app.models.enums import OrgType


class User(Base):
    __tablename__ = "users"
    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role_id = Column(GUID, ForeignKey("roles.id"), nullable=False)
    org_type = Column(
        SAEnum(OrgType, native_enum=False, values_callable=lambda e: [m.value for m in e]),
        nullable=True,
    )
    org_id = Column(GUID, nullable=True)
    # Talaba qaysi universitetga TEGISHLI ekanligini bildiradi (ixtiyoriy).
    # org_type/org_id'dan AJRATILGAN tushuncha: org_type=university bo'lsa
    # bu — "universitet nomidan boshqaruvchi admin" (register-org orqali),
    # university_id esa — "shu universitetning talabasi" (register orqali,
    # oddiy /register). Ikkisini aralashtirib bo'lmaydi — aks holda
    # University Portal haqiqiy talabalarni topa olmaydi (topilgan xato).
    # use_alter=True: users<->universities orasida doiraviy FK bog'liqlik
    # bor (University.verified_by_admin_id -> users.id). Buni belgilamasak
    # SQLAlchemy drop_all()/create_all() uchun jadval tartibini aniqlay
    # olmaydi (CircularDependencyError — sinab tasdiqlangan).
    university_id = Column(
        GUID,
        ForeignKey("universities.id", use_alter=True, name="fk_users_university_id"),
        nullable=True,
    )
    is_active = Column(Boolean, default=True)
    # §30.2: null — email tasdiqlanmagan (bildirishnoma emaillari ketmaydi, ariza berib bo'lmaydi)
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    # §30.3: shu paytdan oldin berilgan JWT'lar (`iat`) bekor
    password_changed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


    role = relationship("Role", back_populates="users", lazy="selectin")
    # CandidateVisibility talent.py da — relationship shu yerda saqlanadi
    visibility = relationship(
        "CandidateVisibility",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )


class AccountToken(Base):
    """Bir martalik havola tokeni (CONTRACT.md §30.1) — bazada faqat SHA-256 xeshi."""
    __tablename__ = "account_tokens"
    __table_args__ = (
        CheckConstraint("purpose IN ('verify_email', 'reset_password')", name="ck_account_tokens_purpose"),
        Index("ix_account_tokens_user_purpose", "user_id", "purpose"),
    )

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    purpose = Column(String(20), nullable=False)
    token_hash = Column(String(64), nullable=False, unique=True)
    email = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
