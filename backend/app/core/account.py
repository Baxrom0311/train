"""
Bir martalik havola tokenlari va hisob xatlari (CONTRACT.md §30.1, §30.5).

Token — `secrets.token_urlsafe(32)`; bazada faqat SHA-256 xeshi. Havolada
token URL fragmentida (`#token=…`) — serverga va `Referer`ga tushmaydi.
"""
import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import AccountToken, User
from app.notifications import mailer

log = logging.getLogger(__name__)


class Purpose(str, Enum):
    VERIFY_EMAIL = "verify_email"
    RESET_PASSWORD = "reset_password"


TTL = {
    Purpose.VERIFY_EMAIL: timedelta(hours=48),
    Purpose.RESET_PASSWORD: timedelta(hours=1),
}
PATH = {
    Purpose.VERIFY_EMAIL: "/verify-email",
    Purpose.RESET_PASSWORD: "/reset-password",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def issue(db: AsyncSession, user: User, purpose: Purpose, now: datetime | None = None) -> str:
    """
    Yangi token (xom qiymat qaytariladi, faqat xatga). Shu foydalanuvchi va
    maqsaddagi ishlatilmagan eskilari o'chadi — faqat oxirgi havola ishlaydi;
    muddati o'tganlari ham shu yerda tozalanadi. Chaqiruvchi commit qiladi.
    """
    now = now or _now()
    await db.execute(
        delete(AccountToken).where(
            AccountToken.user_id == user.id,
            or_(
                and_(AccountToken.purpose == purpose.value, AccountToken.used_at.is_(None)),
                AccountToken.expires_at < now,
            ),
        )
    )
    token = secrets.token_urlsafe(32)
    db.add(AccountToken(
        id=uuid.uuid4(), user_id=user.id, purpose=purpose.value, token_hash=_hash(token),
        email=user.email, created_at=now, expires_at=now + TTL[purpose],
    ))
    return token


async def consume(db: AsyncSession, raw: str, purpose: Purpose, now: datetime | None = None) -> User | None:
    """
    Token yaroqli bo'lsa — `used_at` yoziladi va egasi qaytadi; aks holda None
    (sabab aytilmaydi). Yaroqli: maqsad mos, ishlatilmagan, muddati o'tmagan,
    yuborilgan manzil foydalanuvchining hozirgi email'i. Qator qulflanadi —
    bir token ikki parallel so'rovda ishlatilmaydi. Chaqiruvchi commit qiladi.
    """
    now = now or _now()
    if not raw or len(raw) > 128:
        return None
    row = (await db.execute(
        select(AccountToken, User)
        .join(User, User.id == AccountToken.user_id)
        .where(AccountToken.token_hash == _hash(raw), AccountToken.purpose == purpose.value)
        .with_for_update(of=AccountToken)
    )).first()
    if row is None:
        return None
    record, user = row
    if record.used_at is not None or record.expires_at <= now or record.email != user.email:
        return None
    record.used_at = now
    return user


async def drop_unused(db: AsyncSession, user_id: uuid.UUID, purpose: Purpose) -> None:
    await db.execute(
        delete(AccountToken).where(
            AccountToken.user_id == user_id,
            AccountToken.purpose == purpose.value,
            AccountToken.used_at.is_(None),
        )
    )


def link(purpose: Purpose, token: str) -> str:
    return f"{settings.PUBLIC_URL.rstrip('/')}{PATH[purpose]}#token={token}"


def compose(user: User, purpose: Purpose, token: str) -> mailer.Mail:
    url = link(purpose, token)
    if purpose == Purpose.RESET_PASSWORD:
        subject = "Parolni tiklash"
        body = (
            f"Assalomu alaykum, {user.full_name}!\n\n"
            f"TryJob akkauntingiz uchun parolni tiklash so'raldi. Yangi parol o'rnatish uchun "
            f"havolani oching (1 soat amal qiladi, bir marta ishlaydi):\n\n{url}\n\n"
            f"Parol almashgach barcha qurilmalardagi sessiyalar yopiladi.\n"
            f"Siz so'ramagan bo'lsangiz — bu xatga e'tibor bermang, parolingiz o'zgarmaydi.\n"
        )
    else:
        subject = "Email manzilingizni tasdiqlang"
        body = (
            f"Assalomu alaykum, {user.full_name}!\n\n"
            f"TryJob'da ro'yxatdan o'tganingiz uchun rahmat. Email manzilingizni tasdiqlash uchun "
            f"havolani oching (48 soat amal qiladi):\n\n{url}\n\n"
            f"Tasdiqlangach shu manzilga bildirishnomalar keladi va vakansiyalarga ariza bera olasiz.\n"
            f"Siz ro'yxatdan o'tmagan bo'lsangiz — bu xatga e'tibor bermang.\n"
        )
    return mailer.Mail(to=user.email, subject=f"TryJob — {subject}", body=body + "\n—\nTryJob\n")


async def deliver(mail: mailer.Mail) -> None:
    """`BackgroundTasks`da — javob qaytgandan keyin; xato faqat log'ga (foydalanuvchi qayta so'raydi)."""
    if not mailer.enabled():
        log.warning("hisob xati yuborilmadi: MAIL_BACKEND=off (%s)", mail.subject)
        return
    try:
        ok = await mailer.send([mail])
    except Exception as exc:  # noqa: BLE001 — SMTP ulanmadi
        log.error("hisob xati yuborilmadi (%s): %s", mail.subject, exc)
        return
    if not all(ok):
        log.error("hisob xati yuborilmadi (%s): SMTP rad etdi", mail.subject)
