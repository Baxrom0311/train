"""arq cron'lari (CONTRACT.md §15.2–15.3, §22.2): dedlayn eslatmasi, email va push."""
import logging
from datetime import datetime, timezone

from app.notifications import mailer, push
from app.notifications.emails import send_pending
from app.notifications.run_events import deadline_reminders

log = logging.getLogger(__name__)


def _sessions(ctx: dict):
    if "session_factory" in ctx:
        return ctx["session_factory"]
    from app.database import AsyncSessionLocal
    return AsyncSessionLocal


async def deadline_reminders_job(ctx: dict) -> int:
    async with _sessions(ctx)() as db:
        count = await deadline_reminders(db, datetime.now(timezone.utc))
        await db.commit()
    return count


async def send_notification_emails_job(ctx: dict) -> dict[str, int] | None:
    if not mailer.enabled():
        return None
    async with _sessions(ctx)() as db:
        counts = await send_pending(db, datetime.now(timezone.utc))
        await db.commit()
    if counts["sent"] or counts["failed"]:
        log.info("email bildirishnomalar: %s", counts)
    return counts


async def send_push_notifications_job(ctx: dict) -> dict[str, int] | None:
    if not push.enabled():
        return None
    async with _sessions(ctx)() as db:
        counts = await push.send_pending(db, datetime.now(timezone.utc))
        await db.commit()
    if counts["sent"] or counts["failed"] or counts["removed"]:
        log.info("push bildirishnomalar: %s", counts)
    return counts
