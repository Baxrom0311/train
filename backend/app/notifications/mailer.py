"""
SMTP orqali email (CONTRACT.md §15.3) — stdlib `smtplib`, alohida thread'da.

`SMTP_HOST` bo'sh bo'lsa email o'chirilgan: `enabled()` False, cron hech
narsa yubormaydi. Parol va boshqa sozlamalar faqat `.env`dan.
"""
import asyncio
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

from app.config import settings

TIMEOUT_SECONDS = 15


@dataclass(frozen=True)
class Mail:
    to: str
    subject: str
    body: str


def enabled() -> bool:
    return bool(settings.SMTP_HOST)


def _send_sync(mails: list[Mail]) -> list[bool]:
    """Bitta ulanishda bir nechta xat; har xat uchun natija (bittasi xato bo'lsa qolganlari ketadi)."""
    results: list[bool] = []
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=TIMEOUT_SECONDS) as smtp:
        if settings.SMTP_STARTTLS:
            smtp.starttls()
        if settings.SMTP_USER:
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        for mail in mails:
            msg = EmailMessage()
            msg["From"] = settings.SMTP_FROM
            msg["To"] = mail.to
            msg["Subject"] = mail.subject
            msg.set_content(mail.body)
            try:
                smtp.send_message(msg)
                results.append(True)
            except smtplib.SMTPException:
                results.append(False)
    return results


async def send(mails: list[Mail]) -> list[bool]:
    if not mails:
        return []
    return await asyncio.to_thread(_send_sync, mails)
