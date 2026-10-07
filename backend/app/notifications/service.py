"""
Bildirishnoma yozish (CONTRACT.md §15.2).

`notify` chaqiruvchining tranzaksiyasida ishlaydi va commit qilmaydi:
hodisa (yetkazish, taklif, hisobot) bilan bildirishnoma birga yoziladi
yoki birga bekor bo'ladi. Takroriy chaqiruv (`dedupe_key`) — jim o'tkazib yuboriladi.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationSettings
from app.notifications.kinds import EMAIL_DEFAULT, Kind


async def notify(
    db: AsyncSession,
    user_id: uuid.UUID,
    kind: Kind,
    params: dict,
    link: str,
    key: str,
    at: datetime | None = None,
) -> None:
    await db.execute(
        insert(Notification)
        .values(
            id=uuid.uuid4(), user_id=user_id, kind=kind.value, params=params, link=link,
            dedupe_key=key, created_at=at or datetime.now(timezone.utc),
        )
        .on_conflict_do_nothing(constraint="uq_notifications_user_dedupe")
    )


async def unread_count(db: AsyncSession, user_id: uuid.UUID) -> int:
    return await db.scalar(
        select(func.count()).select_from(Notification)
        .where(Notification.user_id == user_id, Notification.read_at.is_(None))
    ) or 0


async def mark_read(db: AsyncSession, user_id: uuid.UUID, ids: list[uuid.UUID] | None, now: datetime) -> None:
    """`ids` None — hammasi. Boshqa foydalanuvchining id'lari jim e'tiborsiz qoladi."""
    stmt = update(Notification).where(Notification.user_id == user_id, Notification.read_at.is_(None))
    if ids is not None:
        stmt = stmt.where(Notification.id.in_(ids))
    await db.execute(stmt.values(read_at=now))


def email_kinds(settings: NotificationSettings | None) -> set[str]:
    """Foydalanuvchi emailga oladigan turlar; sozlama yo'q bo'lsa — default (§15.1)."""
    if settings is None:
        return {k.value for k in EMAIL_DEFAULT}
    return set(settings.email_kinds) if settings.email_enabled else set()
