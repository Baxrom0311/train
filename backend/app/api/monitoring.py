"""
Xatolarni kuzatish API'si (CONTRACT.md §32.4, §32.5).

`POST /client-errors` — ochiq (xato login sahifasida ham bo'ladi), IP bo'yicha
cheklangan; foydalanuvchi aniqlanmaydi. `/admin/errors` — `view_errors`.
"""
import re
import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import throttle
from app.core.deps import require_permission
from app.core.monitoring import TITLE_MAX, Event, fingerprint, record_events
from app.database import get_db
from app.models.monitoring import ErrorGroup
from app.models.user import User

router = APIRouter(prefix="/api/v1", tags=["monitoring"])

CLIENT_LIMIT = (30, 600)   # 10 daqiqada 30 ta, IP bo'yicha (§32.4)

Source = Literal["api", "worker", "frontend"]
Status = Literal["open", "resolved"]

# Chrome/Edge: "    at fn (https://…/assets/index-ab12.js:1:234)"; Firefox/Safari: "fn@https://…"
_CHROME_FRAME = re.compile(r"^\s*at (?:async )?([^\s(]+) \(")
_GECKO_FRAME = re.compile(r"^([^@\s]+)@")
_DIGITS = re.compile(r"\d+")


class ClientError(BaseModel):
    kind: Literal["error", "unhandledrejection", "render"]
    message: str = Field(min_length=1, max_length=500)
    stack: str = Field(default="", max_length=8000)
    path: str = Field(default="", max_length=300)


def _first_function(stack: str) -> str:
    for line in stack.splitlines():
        for pattern in (_CHROME_FRAME, _GECKO_FRAME):
            m = pattern.match(line)
            if m:
                return m.group(1)
    return ""


def _clean_path(path: str) -> str:
    """Faqat yo'l — `?`/`#`dan keyingisi (masalan `#token=`, §30) saqlanmaydi."""
    return re.split(r"[?#]", path, maxsplit=1)[0] or "/"


def client_event(data: ClientError) -> Event:
    path = _clean_path(data.path)
    message = data.message.strip()
    detail = f"{message}\n\n{data.stack}".strip()
    return Event(
        source="frontend", level="error", title=message[:TITLE_MAX], location=path, detail=detail,
        # fayl hash'i va qator raqamisiz — har deploy yangi guruh ochmaydi
        fingerprint=fingerprint("frontend", data.kind, _DIGITS.sub("0", message), _first_function(data.stack)),
    )


@router.post("/client-errors", status_code=204, response_class=Response)
async def report_client_error(data: ClientError, request: Request):
    limit = throttle.Limit(f"client-error:ip:{throttle.client_ip(request)}", *CLIENT_LIMIT)
    await throttle.consume([limit])
    await record_events([client_event(data)])
    return Response(status_code=204)


# ── Admin ────────────────────────────────────────────────────────────


class ErrorGroupOut(BaseModel):
    id: uuid.UUID
    source: Source
    level: str
    title: str
    location: str
    count: int
    first_seen: datetime
    last_seen: datetime
    status: Status


class ErrorGroupDetail(ErrorGroupOut):
    detail: str
    last_request_id: str | None
    resolved_at: datetime | None
    resolved_by_name: str | None


class ErrorGroupList(BaseModel):
    open_total: int
    items: list[ErrorGroupOut]


async def _group(db: AsyncSession, group_id: uuid.UUID) -> ErrorGroup:
    group = await db.get(ErrorGroup, group_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Error group not found")
    return group


async def _detail(db: AsyncSession, group: ErrorGroup) -> ErrorGroupDetail:
    resolver = await db.get(User, group.resolved_by_id) if group.resolved_by_id else None
    return ErrorGroupDetail(
        **ErrorGroupOut.model_validate(group, from_attributes=True).model_dump(),
        detail=group.detail, last_request_id=group.last_request_id, resolved_at=group.resolved_at,
        resolved_by_name=resolver.full_name if resolver else None,
    )


@router.get("/admin/errors", response_model=ErrorGroupList)
async def list_errors(
    status: Status = "open",
    source: Source | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("view_errors")),
):
    query = select(ErrorGroup).where(ErrorGroup.status == status)
    if source:
        query = query.where(ErrorGroup.source == source)
    items = (await db.execute(query.order_by(ErrorGroup.last_seen.desc()).limit(limit))).scalars().all()
    open_total = (await db.execute(
        select(func.count()).select_from(ErrorGroup).where(ErrorGroup.status == "open")
    )).scalar_one()
    return ErrorGroupList(open_total=open_total, items=[ErrorGroupOut.model_validate(g, from_attributes=True) for g in items])


@router.get("/admin/errors/{group_id}", response_model=ErrorGroupDetail)
async def get_error(
    group_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("view_errors")),
):
    return await _detail(db, await _group(db, group_id))


@router.post("/admin/errors/{group_id}/resolve", response_model=ErrorGroupDetail)
async def resolve_error(
    group_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("view_errors")),
):
    group = await _group(db, group_id)
    if group.status != "resolved":
        group.status = "resolved"
        group.resolved_at = datetime.now(timezone.utc)
        group.resolved_by_id = user.id
        await db.commit()
    return await _detail(db, group)
