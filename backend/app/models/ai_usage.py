"""
AI sarfi hisobi (CONTRACT.md §21.1, Modul 2) — faqat yig'indi sonlar.

Bir kun (Toshkent) + provayder + model + maqsad uchun bitta qator; xabar
matni, foydalanuvchi yoki Run id saqlanmaydi.
"""
from datetime import date

from sqlalchemy import BigInteger, Date, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AIUsage(Base):
    __tablename__ = "ai_usage"

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), primary_key=True)
    model: Mapped[str] = mapped_column(String(100), primary_key=True)
    purpose: Mapped[str] = mapped_column(String(32), primary_key=True)
    calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    tokens_in: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default=text("0"))
    tokens_out: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default=text("0"))
