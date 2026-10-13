"""
Email yuborish (CONTRACT.md §15.3, §30.5) — stdlib `smtplib`, alohida thread'da.

Backend `MAIL_BACKEND`dan: `smtp`, `console` (lokal ishlab chiqish — xat
yuborilmaydi, log'ga yoziladi) yoki `off`. Bo'sh bo'lsa `SMTP_HOST` bor —
`smtp`, yo'q — `off`: `enabled()` False, cron hech narsa yubormaydi.
Parol va boshqa sozlamalar faqat `.env`dan.
"""
import asyncio
import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

from app.config import settings

log = logging.getLogger(__name__)

TIMEOUT_SECONDS = 15


@dataclass(frozen=True)
class Mail:
    to: str
    subject: str
    body: str


def backend() -> str:
    if settings.MAIL_BACKEND:
        return settings.MAIL_BACKEND
    return "smtp" if settings.SMTP_HOST else "off"


def enabled() -> bool:
    return backend() != "off"


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


def _log_console(mails: list[Mail]) -> list[bool]:
    for mail in mails:
        # WARNING — standart log sozlamasida ham ko'rinsin (faqat lokal backend)
        log.warning("console mail → %s\nSubject: %s\n\n%s", mail.to, mail.subject, mail.body)
    return [True] * len(mails)


async def send(mails: list[Mail]) -> list[bool]:
    if not mails:
        return []
    kind = backend()
    if kind == "console":
        return _log_console(mails)
    if kind == "off":
        return [False] * len(mails)
    return await asyncio.to_thread(_send_sync, mails)
