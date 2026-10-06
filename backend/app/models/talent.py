import uuid
from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from sqlalchemy.sql import func
from app.models.rbac import GUID

class TalentOffer(Base):
    __tablename__ = "talent_offers"

    id = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    company_id = mapped_column(GUID, ForeignKey("companies.id"), nullable=False)
    candidate_id = mapped_column(GUID, ForeignKey("users.id"), nullable=False)
    message = mapped_column(String, nullable=False)
    status = mapped_column(String, nullable=False, default="sent", server_default="sent")
    created_at = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
