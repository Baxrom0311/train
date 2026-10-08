"""
Suhbat bosqichlari qoidalari (CONTRACT.md §25): vaqt variantlari, bosqich
raqami, faol suhbatni topish va ariza yopilganda bekor qilish.

Chaqiruvchi ariza qatorini avval qulflaydi (§25.2 qulflash tartibi) va commit qiladi.
"""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ApplicationInterviewStatus
from app.models.talent import ApplicationInterview

MAX_SLOTS = 3
MIN_LEAD = timedelta(hours=1)
MAX_AHEAD = timedelta(days=60)
REMINDER_LEAD = timedelta(hours=2)
ACTIVE = (ApplicationInterviewStatus.PROPOSED, ApplicationInterviewStatus.CONFIRMED)


def normalize_slot(value: datetime) -> datetime:
    """UTC, daqiqagacha. Vaqt mintaqasisiz qiymat — ValueError (Toshkent yoki UTC — mijoz aytishi shart)."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("slot must include a timezone offset")
    return value.astimezone(timezone.utc).replace(second=0, microsecond=0)


def slot_problem(slots: list[datetime], now: datetime) -> str | None:
    """Yaratish paytidagi oyna: har variant [hozir + 1 soat, hozir + 60 kun]."""
    for slot in slots:
        if slot < now + MIN_LEAD:
            return "Each slot must be at least 1 hour from now"
        if slot > now + MAX_AHEAD:
            return "Each slot must be within 60 days"
    return None


def slot_times(interview: ApplicationInterview) -> list[datetime]:
    return [datetime.fromisoformat(s) for s in interview.slots]


def is_expired(interview: ApplicationInterview, now: datetime) -> bool:
    """§25.2: `proposed`, lekin tanlash mumkin bo'lgan variant qolmagan."""
    return interview.status == ApplicationInterviewStatus.PROPOSED and all(s <= now for s in slot_times(interview))


def sort_key(interview: ApplicationInterview) -> datetime:
    return interview.starts_at or slot_times(interview)[0]


async def next_round(db: AsyncSession, application_id: uuid.UUID) -> int:
    done = await db.scalar(
        select(func.count()).select_from(ApplicationInterview).where(
            ApplicationInterview.application_id == application_id,
            ApplicationInterview.status == ApplicationInterviewStatus.COMPLETED,
        )
    )
    return (done or 0) + 1


async def active(db: AsyncSession, application_id: uuid.UUID, *, lock: bool = False) -> ApplicationInterview | None:
    q = select(ApplicationInterview).where(
        ApplicationInterview.application_id == application_id, ApplicationInterview.status.in_(ACTIVE),
    )
    if lock:
        q = q.with_for_update()
    return (await db.execute(q)).scalars().first()


async def close_active(db: AsyncSession, application_id: uuid.UUID, now: datetime) -> ApplicationInterview | None:
    """Ariza taklif/rad/qaytarib olish bilan yopildi — faol suhbat `cancelled` (§25.2). Bekor qilinganini qaytaradi."""
    interview = await active(db, application_id, lock=True)
    if interview is not None:
        interview.status = ApplicationInterviewStatus.CANCELLED
        interview.updated_at = now
    return interview


async def history(db: AsyncSession, application_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[ApplicationInterview]]:
    """Arizalar bo'yicha suhbatlar, yangilari tepada."""
    out: dict[uuid.UUID, list[ApplicationInterview]] = {i: [] for i in application_ids}
    if not application_ids:
        return out
    rows = (await db.execute(
        select(ApplicationInterview)
        .where(ApplicationInterview.application_id.in_(application_ids))
        .order_by(ApplicationInterview.created_at.desc())
    )).scalars()
    for interview in rows:
        out[interview.application_id].append(interview)
    return out
