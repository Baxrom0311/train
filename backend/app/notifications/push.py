"""
Web Push yuborish (CONTRACT.md §22.2) — `pywebpush`, alohida thread'da.

VAPID kalitlari `.env`dan; bo'sh bo'lsa push o'chirilgan (`enabled()` False).
Har bildirishnoma bir marta ko'riladi: `sent`, `skipped` yoki `failed`.
10 daqiqadan eski kutayotganlar `skipped` — kech kelgan push foydasiz.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.notification import Notification, NotificationSettings, PushSubscription
from app.models.user import User
from app.notifications.emails import render

log = logging.getLogger(__name__)

BATCH = 50
MAX_AGE = timedelta(minutes=10)
TTL_SECONDS = 15 * 60
TIMEOUT_SECONDS = 10
GONE = (404, 410)   # obuna bekor qilingan — o'chiriladi


@dataclass(frozen=True)
class Target:
    id: uuid.UUID
    endpoint: str
    p256dh: str
    auth: str


def enabled() -> bool:
    return bool(settings.VAPID_PUBLIC_KEY and settings.VAPID_PRIVATE_KEY and settings.VAPID_SUBJECT)


@lru_cache(maxsize=1)
def _vapid(private_key: str):
    from py_vapid import Vapid

    return Vapid.from_raw(private_key.encode())


def payload(n: Notification) -> str:
    title, body = render(n)
    return json.dumps({"title": title, "body": body, "link": n.link, "tag": str(n.id)}, ensure_ascii=False)


def _send_sync(target: Target, data: str) -> int | None:
    """None — yetkazildi; aks holda HTTP status (yoki 0 — tarmoq xatosi)."""
    from pywebpush import WebPushException, webpush

    try:
        webpush(
            subscription_info={"endpoint": target.endpoint, "keys": {"p256dh": target.p256dh, "auth": target.auth}},
            data=data,
            vapid_private_key=_vapid(settings.VAPID_PRIVATE_KEY),
            vapid_claims={"sub": settings.VAPID_SUBJECT},
            ttl=TTL_SECONDS,
            timeout=TIMEOUT_SECONDS,
        )
        return None
    except WebPushException as exc:
        return exc.response.status_code if exc.response is not None else 0
    except Exception as exc:  # noqa: BLE001 — buzuq kalit, tarmoq: shu obuna xato
        log.warning("push yuborilmadi: %s", exc)
        return 0


async def deliver(target: Target, data: str) -> int | None:
    return await asyncio.to_thread(_send_sync, target, data)


async def send_pending(db: AsyncSession, now: datetime, send=deliver) -> dict[str, int]:
    """Kutayotgan push'larni yuboradi yoki o'tkazib yuboradi. Chaqiruvchi commit qiladi."""
    await db.execute(
        update(Notification)
        .where(Notification.push_status.is_(None), Notification.created_at < now - MAX_AGE)
        .values(push_status="skipped")
    )
    rows = (await db.execute(
        select(Notification, User.is_active, NotificationSettings.push_enabled)
        .join(User, User.id == Notification.user_id)
        .outerjoin(NotificationSettings, NotificationSettings.user_id == Notification.user_id)
        .where(Notification.push_status.is_(None))
        .order_by(Notification.created_at)
        .limit(BATCH)
        .with_for_update(of=Notification, skip_locked=True)
    )).all()
    users = {n.user_id for n, _, _ in rows}
    targets: dict[uuid.UUID, list[Target]] = {}
    if users:
        for s in (await db.execute(select(PushSubscription).where(PushSubscription.user_id.in_(users)))).scalars():
            targets.setdefault(s.user_id, []).append(Target(s.id, s.endpoint, s.p256dh, s.auth))

    counts = {"sent": 0, "skipped": 0, "failed": 0}
    gone: set[uuid.UUID] = set()
    used: set[uuid.UUID] = set()
    for n, active, push_enabled in rows:
        mine = [t for t in targets.get(n.user_id, []) if t.id not in gone]
        # o'qilgan bo'lsa (talaba saytda ko'rdi) push kerak emas
        if n.read_at is not None or not active or push_enabled is False or not mine:
            n.push_status = "skipped"
            counts["skipped"] += 1
            continue
        data = payload(n)
        results = await asyncio.gather(*(send(t, data) for t in mine))
        for t, status in zip(mine, results):
            if status is None:
                used.add(t.id)
            elif status in GONE:
                gone.add(t.id)
        ok = any(status is None for status in results)
        n.push_status = "sent" if ok else "failed"
        counts["sent" if ok else "failed"] += 1

    if gone:
        await db.execute(delete(PushSubscription).where(PushSubscription.id.in_(gone)))
    if used:
        await db.execute(update(PushSubscription).where(PushSubscription.id.in_(used)).values(last_used_at=now))
    counts["removed"] = len(gone)
    return counts
