"""
Xatolarni kuzatish (CONTRACT.md §32): log handler, so'rov middleware'i,
guruhlab yozish, ogohlantirish va tozalash cron'lari.

Oqim: `ERROR`+ log yozuvi → `MonitorHandler` (sinxron, faqat navbatga
qo'yadi) → `Monitor` fon vazifasi har soniyada navbatni bitta sessiyada
`error_groups`ga yozadi. Brauzer xatolari `record_events()` orqali to'g'ridan.
Kuzatuvning o'zi hech qachon so'rovni yoki job'ni buzmaydi: xatolari faqat
`WARNING` log (bu logger yig'ilmaydi — aylanish yo'q).
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import secrets
import time
import traceback
from collections import Counter, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import case, delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert

from app.config import settings
from app.core.logging import request_id_var
from app.models.monitoring import ErrorGroup

log = logging.getLogger(__name__)
access_log = logging.getLogger("app.access")
request_log = logging.getLogger("app.request")

QUEUE_MAX = 1000
FLUSH_INTERVAL = 1.0           # soniya
NEW_GROUPS_PER_HOUR = 200      # bir manbadan (§32.3)
TITLE_MAX = 300
LOCATION_MAX = 300
DETAIL_MAX = 16_000
RESOLVED_TTL = timedelta(days=30)
ANY_TTL = timedelta(days=90)
ALERT_LIST = 10
HEALTH_PATH = "/api/v1/health"

_APP_DIR = Path(__file__).resolve().parents[1]   # .../backend/app
_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,64}")
_CAPTURED = "_tryjob_captured"    # exception'ga belgi — bir xato ikki marta yig'ilmasin


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _clip_detail(text: str) -> str:
    """Boshi (xabar) va oxiri (traceback'ning eng muhim qismi) saqlanadi."""
    if len(text) <= DETAIL_MAX:
        return text
    head = 2000
    return text[:head] + "\n…\n" + text[-(DETAIL_MAX - head - 3):]


def fingerprint(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()


@dataclass
class Event:
    source: str
    level: str
    title: str
    location: str
    detail: str
    fingerprint: str
    request_id: str | None = None
    at: datetime = field(default_factory=_utcnow)


# ── Log yozuvidan hodisa ─────────────────────────────────────────────


def _app_frame(tb) -> str:
    """Eng ichki ilova (`app/`) freymi `fayl:funksiya`; bo'lmasa eng ichki freym."""
    frames = traceback.extract_tb(tb)
    if not frames:
        return ""
    ours = [f for f in frames if f.filename.startswith(f"{_APP_DIR}/")]
    frame = (ours or frames)[-1]
    # "app/core/x.py" — sayt qayerga o'rnatilganidan qat'i nazar bir xil
    path = Path(frame.filename).relative_to(_APP_DIR.parent).as_posix() if ours else Path(frame.filename).name
    return f"{path}:{frame.name}"


def _location(record: logging.LogRecord) -> str:
    explicit = getattr(record, "tj_location", None)
    if explicit:
        return explicit
    # arq: "%6.2fs ! %s failed, %s: %s" — 2-argument `job_id:funksiya` (cron id'sida ham ':' bor)
    if record.name == "arq.worker" and isinstance(record.args, tuple) and len(record.args) >= 2:
        return str(record.args[1]).rsplit(":", 1)[-1]
    return f"{record.name}:{record.funcName}"


def event_from_record(record: logging.LogRecord, source: str) -> Event | None:
    exc = record.exc_info[1] if record.exc_info else None
    if exc is not None and getattr(exc, _CAPTURED, False):
        return None
    location = _clip(_location(record), LOCATION_MAX)
    try:
        message = record.getMessage()
    except Exception:  # noqa: BLE001 — buzuq format argumentlari
        message = str(record.msg)
    if exc is not None:
        try:
            setattr(exc, _CAPTURED, True)
        except (AttributeError, TypeError):
            pass
        kind = f"{type(exc).__module__}.{type(exc).__qualname__}".removeprefix("builtins.")
        title = f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
        fp = fingerprint(source, kind, _app_frame(exc.__traceback__), location)
        detail = message + "\n\n" + "".join(traceback.format_exception(exc))
    else:
        title = message
        fp = fingerprint(source, record.name, str(record.msg))
        detail = message
    return Event(
        source=source, level=record.levelname.lower(), title=_clip(title.strip() or record.name, TITLE_MAX),
        location=location, detail=_clip_detail(detail), fingerprint=fp, request_id=request_id_var.get(),
    )


class MonitorHandler(logging.Handler):
    """Sinxron: yozuvni navbatga qo'yadi, DB'ga `Monitor.flush()` yozadi."""

    def __init__(self, source: str, queue: deque) -> None:
        super().__init__(level=logging.ERROR)
        self.source = source
        self.queue = queue

    def emit(self, record: logging.LogRecord) -> None:
        if record.name == __name__:
            return
        try:
            event = event_from_record(record, self.source)
            if event is not None:
                self.queue.append(event)   # deque(maxlen) — to'lsa eng eskisi tushadi
        except Exception:  # noqa: BLE001 — log chaqiruvi hech qachon yiqilmasin
            self.handleError(record)


# ── DB'ga yozish ─────────────────────────────────────────────────────


def _update_stmt(ev: Event, n: int):
    g = ErrorGroup
    return (
        update(g)
        .where(g.fingerprint == ev.fingerprint)
        .values(
            count=g.count + n,
            last_seen=func.greatest(g.last_seen, ev.at),
            title=ev.title,
            level=ev.level,
            location=ev.location,
            detail=ev.detail,
            last_request_id=func.coalesce(ev.request_id, g.last_request_id),
            # §32.3: hal qilingan xato qaytdi — qayta ochiladi va yana xabar qilinadi
            notified_at=case((g.status == "resolved", None), else_=g.notified_at),
            resolved_at=None,
            resolved_by_id=None,
            status="open",
        )
    )


async def _write(session, ev: Event, n: int, first_seen: datetime) -> None:
    if (await session.execute(_update_stmt(ev, n))).rowcount:
        return
    recent = (await session.execute(
        select(func.count()).select_from(ErrorGroup)
        .where(ErrorGroup.source == ev.source, ErrorGroup.first_seen > ev.at - timedelta(hours=1))
    )).scalar_one()
    if recent >= NEW_GROUPS_PER_HOUR:
        log.warning("xato guruhlari chegarasi (%s): yangi guruh tashlab yuborildi", ev.source)
        return
    inserted = await session.execute(
        insert(ErrorGroup).values(
            fingerprint=ev.fingerprint, source=ev.source, level=ev.level, title=ev.title,
            location=ev.location, detail=ev.detail, count=n, first_seen=first_seen, last_seen=ev.at,
            last_request_id=ev.request_id, status="open",
        ).on_conflict_do_nothing(index_elements=[ErrorGroup.fingerprint])
    )
    if not inserted.rowcount:   # parallel jarayon shu orada qo'shdi
        await session.execute(_update_stmt(ev, n))


async def record_events(events: list[Event]) -> None:
    """Bir xil fingerprint bitta yozuv (oxirgi hodisa tafsiloti, umumiy son). Xato yutiladi."""
    if not events:
        return
    from app.database import AsyncSessionLocal

    counts = Counter(ev.fingerprint for ev in events)
    latest: dict[str, Event] = {}
    first: dict[str, datetime] = {}
    for ev in events:
        if ev.fingerprint not in latest or ev.at >= latest[ev.fingerprint].at:
            latest[ev.fingerprint] = ev
        first[ev.fingerprint] = min(first.get(ev.fingerprint, ev.at), ev.at)
    try:
        async with AsyncSessionLocal() as session:
            for fp, ev in latest.items():
                await _write(session, ev, counts[fp], first[fp])
            await session.commit()
    except Exception as exc:  # noqa: BLE001 — DB ishlamasa ham ilova ishlashda davom etadi
        log.warning("xatolar yozilmadi (%d ta): %s", len(events), exc)


class Monitor:
    """Jarayon uchun bitta: handler + fon yozuvchi. `start`/`stop` — lifespan va worker hook'lari."""

    def __init__(self) -> None:
        self.queue: deque[Event] = deque(maxlen=QUEUE_MAX)
        self.handler: MonitorHandler | None = None
        self._task: asyncio.Task | None = None

    def start(self, source: str) -> None:
        self.stop_capture()
        self.handler = MonitorHandler(source, self.queue)
        logging.getLogger().addHandler(self.handler)
        self._task = asyncio.get_running_loop().create_task(self._loop())

    def stop_capture(self) -> None:
        if self.handler is not None:
            logging.getLogger().removeHandler(self.handler)
            self.handler = None

    async def stop(self) -> None:
        self.stop_capture()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        await self.flush()

    async def flush(self) -> None:
        events = []
        while self.queue:
            events.append(self.queue.popleft())
        await record_events(events)

    async def _loop(self) -> None:
        while True:
            await asyncio.sleep(FLUSH_INTERVAL)
            await self.flush()


monitor = Monitor()


# ── So'rov middleware'i (§32.2) ──────────────────────────────────────


def _route(scope) -> str:
    route = scope.get("route")
    return getattr(route, "path", None) or scope.get("path", "")


class RequestContextMiddleware:
    """`X-Request-ID`, access log va kutilmagan xatoni 500 + `request_id` ga aylantirish."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        incoming = dict(scope.get("headers") or []).get(b"x-request-id", b"").decode("latin-1")
        rid = incoming if _REQUEST_ID.fullmatch(incoming) else secrets.token_hex(16)
        token = request_id_var.set(rid)
        started = time.perf_counter()
        state = {"status": 500, "started": False}

        async def send_wrapper(message) -> None:
            if message["type"] == "http.response.start":
                state["status"] = message["status"]
                state["started"] = True
                message["headers"] = [*message.get("headers", []), (b"x-request-id", rid.encode())]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            where = f"{scope['method']} {_route(scope)}"
            request_log.exception("kutilmagan xato: %s", where, extra={"tj_location": where})
            if state["started"]:
                raise   # javob yarmida (SSE) — ulanishni server yopadi; xato allaqachon belgilangan
            await _send_500(send_wrapper, rid)
        finally:
            duration = round((time.perf_counter() - started) * 1000)
            level = logging.DEBUG if scope["path"] == HEALTH_PATH else logging.INFO
            access_log.log(
                level, "%s %s %d %dms", scope["method"], scope["path"], state["status"], duration,
                extra={"method": scope["method"], "path": scope["path"], "status": state["status"],
                       "duration_ms": duration},
            )
            request_id_var.reset(token)


async def _send_500(send, rid: str) -> None:
    body = json.dumps({"detail": "Internal Server Error", "request_id": rid}).encode()
    await send({
        "type": "http.response.start", "status": 500,
        "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())],
    })
    await send({"type": "http.response.body", "body": body})


# ── Cron'lar (worker) ────────────────────────────────────────────────


def _alert_mail(user, groups: list[ErrorGroup], total: int):
    from app.notifications import mailer

    url = settings.PUBLIC_URL.rstrip("/") + "/admin?tab=errors"
    lines = [f"• [{g.source}] {g.title}\n  {g.location} — {g.count} marta" for g in groups[:ALERT_LIST]]
    if total > ALERT_LIST:
        lines.append(f"… va yana {total - ALERT_LIST} ta")
    body = (
        f"Assalomu alaykum, {user.full_name}!\n\nPlatformada yangi xatolar paydo bo'ldi:\n\n"
        + "\n".join(lines) + f"\n\nBatafsil: {url}\n\n—\nTryJob xatolar kuzatuvi\n"
    )
    return mailer.Mail(to=user.email, subject=f"TryJob — {total} ta yangi xato", body=body)


async def send_alerts(db, now: datetime, send=None) -> int:
    """Xabar qilinmagan ochiq guruhlar — `view_errors` egalariga bitta xat. Chaqiruvchi commit qiladi."""
    from app.models.rbac import Permission, Role, role_permissions
    from app.models.user import User
    from app.notifications import mailer

    groups = list((await db.execute(
        select(ErrorGroup)
        .where(ErrorGroup.status == "open", ErrorGroup.notified_at.is_(None))
        .order_by(ErrorGroup.last_seen.desc())
        .with_for_update(skip_locked=True)
    )).scalars())
    if not groups:
        return 0
    if mailer.enabled():
        users = (await db.execute(
            select(User)
            .join(Role, Role.id == User.role_id)
            .join(role_permissions, role_permissions.c.role_id == Role.id)
            .join(Permission, Permission.id == role_permissions.c.permission_id)
            .where(Permission.key == "view_errors", User.is_active.is_(True), User.email_verified_at.is_not(None))
        )).scalars().all()
        mails = [_alert_mail(u, groups, len(groups)) for u in users]
        try:
            await (send or mailer.send)(mails)
        except Exception as exc:  # noqa: BLE001 — SMTP ulanmadi; xatolar sahifada baribir ko'rinadi
            log.warning("xato ogohlantirishi yuborilmadi: %s", exc)
    for g in groups:
        g.notified_at = now
    return len(groups)


async def cleanup(db, now: datetime) -> int:
    result = await db.execute(delete(ErrorGroup).where(or_(
        (ErrorGroup.status == "resolved") & (ErrorGroup.last_seen < now - RESOLVED_TTL),
        ErrorGroup.last_seen < now - ANY_TTL,
    )))
    return result.rowcount


async def error_alerts_job(ctx: dict) -> int:  # noqa: ARG001
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        sent = await send_alerts(db, _utcnow())
        await db.commit()
    return sent


async def error_maintenance_job(ctx: dict) -> int:  # noqa: ARG001
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        removed = await cleanup(db, _utcnow())
        await db.commit()
    return removed
