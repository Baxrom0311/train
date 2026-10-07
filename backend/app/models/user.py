import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, Enum as SAEnum
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
    is_active = Column(Boolean, default=True)
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
