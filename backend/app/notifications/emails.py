"""
Email matni (o'zbekcha) va yuborish cron'i (CONTRACT.md §15.3).

Har bildirishnoma bir marta ko'riladi: `sent`, `skipped` yoki `failed`.
1 soatdan eski kutayotganlar emailga ketmaydi (SMTP keyin yoqilsa ham
eski bildirishnomalar yog'ilib kelmasin) — ular `skipped`.
"""
import logging
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.notification import Notification, NotificationSettings
from app.models.user import User
from app.notifications import mailer
from app.notifications.kinds import Kind
from app.notifications.service import email_kinds
from app.scenario.clock import TASHKENT

log = logging.getLogger(__name__)

BATCH = 50
MAX_AGE = timedelta(hours=1)


def _hhmm(iso: str | None) -> str:
    return datetime.fromisoformat(iso).astimezone(TASHKENT).strftime("%H:%M") if iso else ""


def render(n: Notification) -> tuple[str, str]:
    """(mavzu, birinchi abzas) — havola va imzo `compose`da qo'shiladi."""
    p = n.params
    kind = Kind(n.kind)
    if kind == Kind.TASK_DELIVERED:
        due = f" Dedlayn — {_hhmm(p['due_at'])} (Toshkent vaqti)." if p.get("due_at") else ""
        return f"Yangi vazifa: {p['title']}", f"Ish stolingizga yangi vazifa keldi: «{p['title']}».{due}"
    if kind == Kind.DEADLINE_SOON:
        return f"Dedlayn yaqin: {p['title']}", f"«{p['title']}» dedlayni {_hhmm(p['due_at'])} da (Toshkent vaqti). Javob hali topshirilmagan."
    if kind == Kind.MENTOR_REVIEW:
        return f"Mentor izohi: {p['title']}", f"{p['mentor']} «{p['title']}» bo'yicha javobingizga izoh yozdi."
    if kind == Kind.REPORT_READY:
        extra = f" Sertifikat kodi: {p['code']}." if p.get("code") else ""
        return f"Yakuniy hisobot: {p['scenario_title']}", f"«{p['scenario_title']}» ssenariysi bo'yicha yakuniy hisobotingiz tayyor.{extra}"
    if kind == Kind.OFFER_RECEIVED:
        return f"Ish taklifi: {p['position']}", f"{p['company']} sizga «{p['position']}» lavozimiga taklif yubordi."
    answer = "qabul qildi" if p.get("accepted") else "rad etdi"
    return f"Taklifga javob: {p['position']}", f"{p['candidate']} «{p['position']}» taklifingizni {answer}."


def compose(n: Notification, user: User) -> mailer.Mail:
    subject, lead = render(n)
    url = settings.PUBLIC_URL.rstrip("/") + n.link
    body = (
        f"Assalomu alaykum, {user.full_name}!\n\n{lead}\n\nOchish: {url}\n\n"
        f"—\nTryJob. Email bildirishnomalarni sozlash: {settings.PUBLIC_URL.rstrip('/')}/notifications\n"
    )
    return mailer.Mail(to=user.email, subject=f"TryJob — {subject}", body=body)


async def send_pending(db: AsyncSession, now: datetime, send=mailer.send) -> dict[str, int]:
    """Kutayotganlarni yuboradi yoki o'tkazib yuboradi. Chaqiruvchi commit qiladi."""
    await db.execute(
        update(Notification)
        .where(Notification.email_status.is_(None), Notification.created_at < now - MAX_AGE)
        .values(email_status="skipped")
    )
    rows = (await db.execute(
        select(Notification, User, NotificationSettings)
        .join(User, User.id == Notification.user_id)
        .outerjoin(NotificationSettings, NotificationSettings.user_id == Notification.user_id)
        .where(Notification.email_status.is_(None))
        .order_by(Notification.created_at)
        .limit(BATCH)
        .with_for_update(of=Notification, skip_locked=True)
    )).all()
    counts = {"sent": 0, "skipped": 0, "failed": 0}
    outgoing: list[tuple[Notification, mailer.Mail]] = []
    for n, user, prefs in rows:
        # o'qilgan bo'lsa (talaba saytda ko'rdi) email kerak emas
        if n.read_at is not None or not user.is_active or n.kind not in email_kinds(prefs):
            n.email_status = "skipped"
            counts["skipped"] += 1
        else:
            outgoing.append((n, compose(n, user)))
    try:
        results = await send([m for _, m in outgoing])
    except Exception as exc:  # noqa: BLE001 — SMTP ulanmadi: partiya `failed`, qayta urinilmaydi
        log.error("email yuborilmadi (%d ta): %s", len(outgoing), exc)
        results = [False] * len(outgoing)
    for (n, _), ok in zip(outgoing, results):
        n.email_status = "sent" if ok else "failed"
        n.emailed_at = now if ok else None
        counts["sent" if ok else "failed"] += 1
    return counts
