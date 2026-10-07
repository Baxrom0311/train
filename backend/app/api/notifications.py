"""
Bildirishnomalar API (CONTRACT.md §15.4) va push obunalari (§22.3) — har kim
faqat o'zinikini ko'radi.

Ruxsat talab qilinmaydi: ro'yxat foydalanuvchining o'z qatorlari bilan
cheklangan; qaysi turlarni sozlash mumkinligi ruxsatlardan (`available_for`).
"""
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user
from app.database import get_db
from app.config import settings as app_settings
from app.models.notification import Notification, NotificationSettings, PushSubscription
from app.models.user import User
from app.notifications import push
from app.notifications.kinds import EMAIL_DEFAULT, Kind, available_for
from app.notifications.service import mark_read, unread_count

users_router = APIRouter(prefix="/api/v1/users", tags=["notifications"])
router = APIRouter(prefix="/api/v1/push", tags=["notifications"])

Me = Annotated[User, Depends(get_current_active_user)]
PAGE_MAX = 50
MAX_SUBSCRIPTIONS = 10   # §22.2: bitta foydalanuvchida — eskisi o'chiriladi


class NotificationOut(BaseModel):
    id: uuid.UUID
    kind: Kind
    params: dict
    link: str
    created_at: datetime
    read_at: datetime | None


class NotificationPage(BaseModel):
    items: list[NotificationOut]
    unread: int


class Unread(BaseModel):
    unread: int


class ReadIn(BaseModel):
    ids: list[uuid.UUID] | None = None
    all: bool = False

    @model_validator(mode="after")
    def _one(self) -> "ReadIn":
        if self.all == (self.ids is not None):
            raise ValueError("ids yoki all — aynan bittasi")
        return self


class SettingsIn(BaseModel):
    email_enabled: bool
    email_kinds: list[Kind]
    push_enabled: bool = True


class PushConfig(BaseModel):
    enabled: bool
    public_key: str | None


class PushKeys(BaseModel):
    p256dh: str = Field(min_length=20, max_length=200)
    auth: str = Field(min_length=8, max_length=100)


class SubscriptionIn(BaseModel):
    endpoint: str = Field(pattern=r"^https://", max_length=1000)
    keys: PushKeys


class SubscriptionRef(BaseModel):
    endpoint: str = Field(max_length=1000)


class SettingsOut(SettingsIn):
    available: list[Kind]


def _permissions(user: User) -> set[str]:
    return {p.key for p in user.role.permissions} if user.role else set()


@users_router.get("/me/notifications", response_model=NotificationPage)
async def list_notifications(
    me: Me,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=PAGE_MAX),
    before: datetime | None = None,
):
    stmt = select(Notification).where(Notification.user_id == me.id)
    if before is not None:
        stmt = stmt.where(Notification.created_at < before)
    rows = (await db.execute(stmt.order_by(Notification.created_at.desc()).limit(limit))).scalars().all()
    return NotificationPage(
        items=[NotificationOut.model_validate(n, from_attributes=True) for n in rows],
        unread=await unread_count(db, me.id),
    )


@users_router.get("/me/notifications/unread", response_model=Unread)
async def get_unread(me: Me, db: AsyncSession = Depends(get_db)):
    return Unread(unread=await unread_count(db, me.id))


@users_router.post("/me/notifications/read", response_model=Unread)
async def read_notifications(body: ReadIn, me: Me, db: AsyncSession = Depends(get_db)):
    await mark_read(db, me.id, None if body.all else body.ids, datetime.now(timezone.utc))
    await db.commit()
    return Unread(unread=await unread_count(db, me.id))


@users_router.get("/me/notification-settings", response_model=SettingsOut)
async def get_settings(me: Me, db: AsyncSession = Depends(get_db)):
    available = available_for(_permissions(me))
    prefs = await db.get(NotificationSettings, me.id)
    # email o'chirilgan bo'lsa ham tanlangan turlar saqlanadi — qayta yoqilganda tiklanadi
    chosen = set(prefs.email_kinds) if prefs else {k.value for k in EMAIL_DEFAULT}
    return SettingsOut(
        email_enabled=prefs.email_enabled if prefs else True,
        email_kinds=[k for k in available if k.value in chosen],
        push_enabled=prefs.push_enabled if prefs else True,
        available=available,
    )


@users_router.put("/me/notification-settings", response_model=SettingsOut)
async def put_settings(body: SettingsIn, me: Me, db: AsyncSession = Depends(get_db)):
    available = available_for(_permissions(me))
    if not set(body.email_kinds) <= set(available):
        raise HTTPException(status_code=422, detail="Notification kind not available for this account")
    prefs = await db.get(NotificationSettings, me.id)
    if prefs is None:
        prefs = NotificationSettings(user_id=me.id)
        db.add(prefs)
    prefs.email_enabled = body.email_enabled
    prefs.email_kinds = sorted({k.value for k in body.email_kinds})
    prefs.push_enabled = body.push_enabled
    await db.commit()
    return SettingsOut(
        email_enabled=prefs.email_enabled,
        email_kinds=[k for k in available if k.value in prefs.email_kinds],
        push_enabled=prefs.push_enabled,
        available=available,
    )


# ── Push (§22.3) ──────────────────────────────────────────────────────


@router.get("/config", response_model=PushConfig)
async def push_config():
    """Ochiq: brauzer obuna uchun ochiq VAPID kalitini oladi."""
    on = push.enabled()
    return PushConfig(enabled=on, public_key=app_settings.VAPID_PUBLIC_KEY if on else None)


@users_router.post("/me/push-subscriptions", status_code=status.HTTP_204_NO_CONTENT)
async def subscribe_push(
    body: SubscriptionIn, me: Me, db: AsyncSession = Depends(get_db),
    user_agent: Annotated[str | None, Header()] = None,
):
    if not push.enabled():
        raise HTTPException(status_code=409, detail="Push notifications are disabled on this server")
    # bitta brauzer — bitta obuna: boshqa akkaunt bilan kirilgan bo'lsa yangi egaga o'tadi
    await db.execute(
        insert(PushSubscription)
        .values(
            id=uuid.uuid4(), user_id=me.id, endpoint=body.endpoint, p256dh=body.keys.p256dh,
            auth=body.keys.auth, user_agent=(user_agent or "")[:200] or None, created_at=datetime.now(timezone.utc),
        )
        .on_conflict_do_update(
            index_elements=[PushSubscription.endpoint],
            set_={"user_id": me.id, "p256dh": body.keys.p256dh, "auth": body.keys.auth},
        )
    )
    extra = (await db.execute(
        select(PushSubscription.id).where(PushSubscription.user_id == me.id)
        .order_by(PushSubscription.created_at.desc(), PushSubscription.id).offset(MAX_SUBSCRIPTIONS)
    )).scalars().all()
    if extra:
        await db.execute(delete(PushSubscription).where(PushSubscription.id.in_(extra)))
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@users_router.delete("/me/push-subscriptions", status_code=status.HTTP_204_NO_CONTENT)
async def unsubscribe_push(body: SubscriptionRef, me: Me, db: AsyncSession = Depends(get_db)):
    """Faqat o'z obunasi o'chadi; boshqaniki yoki yo'q — baribir 204 (mavjudligi oshkor bo'lmaydi)."""
    await db.execute(
        delete(PushSubscription).where(PushSubscription.user_id == me.id, PushSubscription.endpoint == body.endpoint)
    )
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
