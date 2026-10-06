import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.rbac import GUID

class User(Base):
    __tablename__ = "users"
    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role_id = Column(GUID, ForeignKey("roles.id"), nullable=False)
    org_type = Column(String, nullable=True) # company | university
    org_id = Column(GUID, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    role = relationship("Role", back_populates="users", lazy="selectin")
    visibility = relationship("CandidateVisibility", back_populates="user", uselist=False, cascade="all, delete-orphan")

class CandidateVisibility(Base):
    __tablename__ = "candidate_visibility"
    user_id = Column(GUID, ForeignKey("users.id"), primary_key=True)
    is_open_to_work = Column(Boolean, default=False)
    hidden_from_company_ids = Column(JSON, default=list)
    
    user = relationship("User", back_populates="visibility")
