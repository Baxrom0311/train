"""
AI sarfini yozish va narxlash (CONTRACT.md §21.1).

`chat()` har provayder urinishidan keyin `record()`ni chaqiradi. Yozuv
alohida qisqa sessiyada — chaqiruvchining tranzaksiyasiga aralashmaydi;
DB yozib bo'lmasa faqat log (hisob AI ishini to'xtatmaydi).
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from sqlalchemy.dialects.postgresql import insert

from app.config import settings
from app.models.ai_usage import AIUsage
from app.scenario.clock import TASHKENT

log = logging.getLogger(__name__)

PURPOSES = ("evaluation", "persona", "mentor", "day_report", "final_report", "interview", "other")


def today(now: datetime | None = None) -> date:
    return (now or datetime.now(timezone.utc)).astimezone(TASHKENT).date()


def cost_usd(provider: str, tokens_in: int, tokens_out: int) -> float | None:
    """1M token narxi `LLM_PRICES`dan; narxi yo'q provayder — None."""
    price = settings.llm_prices.get(provider)
    if price is None:
        return None
    return (tokens_in * price[0] + tokens_out * price[1]) / 1_000_000


async def record(
    provider: str, model: str, purpose: str, *, tokens_in: int = 0, tokens_out: int = 0, failed: bool = False,
) -> None:
    from app.database import AsyncSessionLocal

    values = {
        "day": today(), "provider": provider, "model": model[:100],
        "purpose": purpose if purpose in PURPOSES else "other",
        "calls": 0 if failed else 1, "failures": 1 if failed else 0,
        "tokens_in": tokens_in, "tokens_out": tokens_out,
    }
    stmt = insert(AIUsage).values(**values)
    stmt = stmt.on_conflict_do_update(
        index_elements=[AIUsage.day, AIUsage.provider, AIUsage.model, AIUsage.purpose],
        set_={
            k: getattr(AIUsage, k) + getattr(stmt.excluded, k)
            for k in ("calls", "failures", "tokens_in", "tokens_out")
        },
    )
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(stmt)
            await session.commit()
    except Exception as exc:  # noqa: BLE001 — hisob yozilmasa ham AI javobi qaytadi
        log.warning("AI sarfi yozilmadi (%s/%s): %s", provider, purpose, exc)
