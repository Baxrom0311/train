"""
Bildirishnomalar API (CONTRACT.md §15.4) — har kim faqat o'zinikini ko'radi.

Ruxsat talab qilinmaydi: ro'yxat foydalanuvchining o'z qatorlari bilan
cheklangan; qaysi turlarni sozlash mumkinligi ruxsatlardan (`available_for`).
"""
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user
from app.database import get_db
from app.models.notification import Notification, NotificationSettings
from app.models.user import User
from app.notifications.kinds import EMAIL_DEFAULT, Kind, available_for
from app.notifications.service import mark_read, unread_count

users_router = APIRouter(prefix="/api/v1/users", tags=["notifications"])

Me = Annotated[User, Depends(get_current_active_user)]
PAGE_MAX = 50


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
    await db.commit()
    return SettingsOut(
        email_enabled=prefs.email_enabled,
        email_kinds=[k for k in available if k.value in prefs.email_kinds],
        available=available,
    )
