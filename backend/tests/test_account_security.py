"""
Hisob xavfsizligi (CONTRACT.md §30): email tasdiqlash, parolni tiklash,
sessiyalarni bekor qilish, urinishlarni cheklash va xat backend'i.
"""
import logging
import re
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, update

from app.config import settings
from app.core import account, throttle
from app.core.account import Purpose
from app.main import app
from app.models.notification import Notification
from app.models.user import AccountToken, User
from app.notifications import emails, mailer
from app.notifications.kinds import Kind
from app.notifications.service import notify

LOGIN = "/api/v1/auth/login"
FORGOT = "/api/v1/auth/password/forgot"
RESET = "/api/v1/auth/password/reset"
VERIFY = "/api/v1/auth/verify-email"
RESEND = "/api/v1/auth/verify-email/resend"
ME = "/api/v1/users/me"


@pytest.fixture
def outbox(monkeypatch) -> list[mailer.Mail]:
    """SMTP o'rniga — yuborilgan xatlar shu ro'yxatga tushadi."""
    sent: list[mailer.Mail] = []

    async def capture(mails):
        sent.extend(mails)
        return [True] * len(mails)

    monkeypatch.setattr(settings, "MAIL_BACKEND", "smtp")
    monkeypatch.setattr(mailer, "send", capture)
    return sent


def _token(mail: mailer.Mail, path: str) -> str:
    match = re.search(rf"{re.escape(settings.PUBLIC_URL.rstrip('/'))}{path}#token=([\w-]+)", mail.body)
    assert match, mail.body
    return match.group(1)


async def _login(client: AsyncClient, email: str, password: str):
    return await client.post(LOGIN, data={"username": email, "password": password})


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _client_from(ip: str) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app, client=(ip, 40000)), base_url="http://test")


async def _register(client: AsyncClient, email: str = "new@example.com", password: str = "password123") -> dict:
    r = await client.post("/api/v1/auth/register", json={"email": email, "password": password, "full_name": "Yangi Talaba"})
    assert r.status_code == 200, r.text
    return r.json()


# ── Email tasdiqlash ─────────────────────────────────────────────────


async def test_register_sends_verification_and_link_verifies(client, outbox, db_session):
    tokens = await _register(client)
    me = (await client.get(ME, headers=_bearer(tokens["access_token"]))).json()
    assert me["email_verified"] is False

    assert len(outbox) == 1 and outbox[0].to == "new@example.com"
    raw = _token(outbox[0], "/verify-email")
    stored = (await db_session.execute(select(AccountToken))).scalars().one()
    assert stored.token_hash != raw and raw not in stored.token_hash     # bazada faqat xesh

    r = await client.post(VERIFY, json={"token": raw})
    assert r.status_code == 200 and r.json() == {"email": "new@example.com", "verified": True}
    me = (await client.get(ME, headers=_bearer(tokens["access_token"]))).json()
    assert me["email_verified"] is True

    again = await client.post(VERIFY, json={"token": raw})                # bir martalik
    assert again.status_code == 400 and again.json()["detail"] == "invalid_token"


async def test_org_signup_can_verify_without_logging_in(client, outbox, db_session):
    r = await client.post("/api/v1/auth/register-org", json={
        "email": "hr@lazurit.uz", "password": "password123", "full_name": "HR",
        "org_type": "company", "org_name": "Lazurit Systems", "industry": "IT",
    })
    assert r.status_code == 202
    assert (await client.post(VERIFY, json={"token": _token(outbox[0], "/verify-email")})).status_code == 200
    user = (await db_session.execute(select(User).where(User.email == "hr@lazurit.uz"))).scalars().one()
    assert user.is_active is False and user.email_verified_at is not None


async def test_verification_token_rules(client, outbox, db_session):
    await _register(client)
    raw = _token(outbox[0], "/verify-email")

    # boshqa maqsad tokeni bilan tasdiqlab bo'lmaydi
    assert (await client.post(VERIFY, json={"token": "x" * 43})).status_code == 400
    # email o'zgargan bo'lsa — eski manzilga ketgan havola yaroqsiz
    await db_session.execute(update(User).values(email="other@example.com"))
    await db_session.commit()
    assert (await client.post(VERIFY, json={"token": raw})).status_code == 400
    await db_session.execute(update(User).values(email="new@example.com"))
    # muddati o'tgan
    await db_session.execute(update(AccountToken).values(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)))
    await db_session.commit()
    assert (await client.post(VERIFY, json={"token": raw})).status_code == 400


async def test_resend_replaces_previous_link_and_is_limited(client, outbox):
    tokens = await _register(client)
    headers = _bearer(tokens["access_token"])
    first = _token(outbox[0], "/verify-email")

    r = await client.post(RESEND, headers=headers)
    assert r.status_code == 202
    second = _token(outbox[1], "/verify-email")
    assert (await client.post(VERIFY, json={"token": first})).status_code == 400   # faqat oxirgi havola
    assert (await client.post(VERIFY, json={"token": second})).status_code == 200
    assert (await client.post(RESEND, headers=headers)).status_code == 409


async def test_resend_rate_limit(client, test_user_factory):
    await test_user_factory("slow@example.com", "password123", email_verified=False)
    access = (await _login(client, "slow@example.com", "password123")).json()["access_token"]
    codes = [(await client.post(RESEND, headers=_bearer(access))).status_code for _ in range(4)]
    assert codes == [202, 202, 202, 429]


async def test_unverified_student_cannot_apply_to_vacancy(client, test_user_factory):
    await test_user_factory("u@example.com", "password123", email_verified=False)
    await test_user_factory("v@example.com", "password123")
    unverified = (await _login(client, "u@example.com", "password123")).json()["access_token"]
    verified = (await _login(client, "v@example.com", "password123")).json()["access_token"]
    path = f"/api/v1/vacancies/{uuid.uuid4()}/apply"

    r = await client.post(path, json={}, headers=_bearer(unverified))
    assert r.status_code == 403 and r.json()["detail"] == "email_not_verified"
    assert (await client.post(path, json={}, headers=_bearer(verified))).status_code == 404


async def test_notification_emails_skip_unverified_address(db_session, test_user_factory):
    now = datetime.now(timezone.utc)
    stranger = await test_user_factory("typo@example.com", "password123", email_verified=False)
    owner = await test_user_factory("owner@example.com", "password123")
    for user in (stranger, owner):
        await notify(db_session, user.id, Kind.OFFER_RECEIVED, {"offer_id": "1", "company": "Lazurit", "position": "QA"},
                     "/offers", "offer:1")
    await db_session.commit()

    sent: list[mailer.Mail] = []

    async def out(mails):
        sent.extend(mails)
        return [True] * len(mails)

    assert await emails.send_pending(db_session, now, send=out) == {"sent": 1, "skipped": 1, "failed": 0}
    assert [m.to for m in sent] == ["owner@example.com"]
    status = dict((await db_session.execute(select(Notification.user_id, Notification.email_status))).all())
    assert status[stranger.id] == "skipped"


# ── Parolni tiklash ──────────────────────────────────────────────────


async def test_forgot_password_never_reveals_accounts(client, outbox, test_user_factory):
    await test_user_factory("known@example.com", "password123")
    await test_user_factory("pending@example.com", "password123", is_active=False)

    for email in ("known@example.com", "ghost@example.com", "pending@example.com"):
        r = await client.post(FORGOT, json={"email": email})
        assert r.status_code == 202 and r.json() == {"status": "sent"}
    assert [m.to for m in outbox] == ["known@example.com"]          # faqat mavjud va faolga
    assert "/reset-password#token=" in outbox[0].body and "e'tibor bermang" in outbox[0].body


async def test_reset_password_changes_password_and_ends_sessions(client, outbox, test_user_factory, db_session):
    user = await test_user_factory("reset@example.com", "old-password", email_verified=False)
    old = (await _login(client, "reset@example.com", "old-password")).json()

    await client.post(FORGOT, json={"email": "reset@example.com"})
    raw = _token(outbox[0], "/reset-password")
    r = await client.post(RESET, json={"token": raw, "password": "new-password"})
    assert r.status_code == 204

    assert (await _login(client, "reset@example.com", "old-password")).status_code == 400
    fresh = await _login(client, "reset@example.com", "new-password")
    assert fresh.status_code == 200
    # parol tiklashdan oldingi access va refresh tokenlar endi ishlamaydi
    assert (await client.get(ME, headers=_bearer(old["access_token"]))).status_code == 401
    assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": old["refresh_token"]})).status_code == 401
    me = await client.get(ME, headers=_bearer(fresh.json()["access_token"]))
    assert me.status_code == 200 and me.json()["email_verified"] is True   # havola egalikni isbotladi

    assert (await client.post(RESET, json={"token": raw, "password": "third-password"})).status_code == 400
    await db_session.refresh(user)
    assert user.password_changed_at is not None


async def test_only_latest_reset_link_works_and_expires(client, outbox, test_user_factory, db_session):
    await test_user_factory("twice@example.com", "password123")
    await client.post(FORGOT, json={"email": "twice@example.com"})
    await client.post(FORGOT, json={"email": "twice@example.com"})
    first, second = (_token(m, "/reset-password") for m in outbox)

    assert (await client.post(RESET, json={"token": first, "password": "new-password"})).status_code == 400
    await db_session.execute(update(AccountToken).values(expires_at=datetime.now(timezone.utc)))
    await db_session.commit()
    assert (await client.post(RESET, json={"token": second, "password": "new-password"})).status_code == 400


async def test_reset_validates_password_and_token_shape(client):
    assert (await client.post(RESET, json={"token": "abc", "password": "short"})).status_code == 422
    assert (await client.post(RESET, json={"token": "a" * 200, "password": "long-enough"})).status_code == 422
    r = await client.post(RESET, json={"token": "nope", "password": "long-enough"})
    assert r.status_code == 400 and r.json()["detail"] == "invalid_token"


async def test_reset_tokens_are_not_verification_tokens(client, outbox, db_session):
    tokens = await _register(client)
    await client.post(FORGOT, json={"email": "new@example.com"})
    reset_raw = _token(outbox[1], "/reset-password")
    assert (await client.post(VERIFY, json={"token": reset_raw})).status_code == 400
    me = (await client.get(ME, headers=_bearer(tokens["access_token"]))).json()
    assert me["email_verified"] is False


async def test_forgot_password_rate_limit(client, outbox, test_user_factory):
    await test_user_factory("spam@example.com", "password123")
    codes = [(await client.post(FORGOT, json={"email": "spam@example.com"})).status_code for _ in range(3)]
    codes.append((await client.post(FORGOT, json={"email": "SPAM@example.com"})).status_code)  # registr aylanmaydi
    assert codes == [202, 202, 202, 429]
    assert len(outbox) == 3


async def test_issue_purges_expired_tokens(db_session, test_user_factory):
    user = await test_user_factory("purge@example.com", "password123")
    past = datetime.now(timezone.utc) - timedelta(days=3)
    await account.issue(db_session, user, Purpose.VERIFY_EMAIL, now=past)
    await account.issue(db_session, user, Purpose.RESET_PASSWORD)
    await db_session.commit()
    purposes = (await db_session.execute(select(AccountToken.purpose))).scalars().all()
    assert purposes == ["reset_password"]


# ── Login urinishlarini cheklash ────────────────────────────────────


async def test_login_locks_after_five_failures_from_same_place(client, test_user_factory):
    await test_user_factory("victim@example.com", "right-password")
    for _ in range(5):
        assert (await _login(client, "victim@example.com", "wrong")).status_code == 400

    locked = await _login(client, "victim@example.com", "right-password")   # to'g'ri parol ham kutadi
    assert locked.status_code == 429
    detail = locked.json()["detail"]
    assert detail["code"] == "too_many_attempts" and 0 < detail["retry_after"] <= 15 * 60
    assert locked.headers["Retry-After"] == str(detail["retry_after"])

    # boshqa joydan egasi kira oladi — akkaunt bo'yicha umumiy chegara 20
    async with _client_from("10.1.1.1") as other:
        assert (await _login(other, "VICTIM@example.com", "wrong")).status_code == 400
        assert (await _login(other, "victim@example.com", "right-password")).status_code == 200


async def test_successful_login_resets_counter(client, test_user_factory):
    await test_user_factory("forgetful@example.com", "right-password")
    for _ in range(4):
        await _login(client, "forgetful@example.com", "wrong")
    assert (await _login(client, "forgetful@example.com", "right-password")).status_code == 200
    for _ in range(4):
        assert (await _login(client, "forgetful@example.com", "wrong")).status_code == 400
    assert (await _login(client, "forgetful@example.com", "right-password")).status_code == 200


async def test_distributed_guessing_locks_account(test_user_factory):
    await test_user_factory("target@example.com", "right-password")
    for i in range(20):
        async with _client_from(f"10.0.0.{i}") as c:
            assert (await _login(c, "target@example.com", "wrong")).status_code == 400
    async with _client_from("10.0.1.1") as fresh:
        assert (await _login(fresh, "target@example.com", "right-password")).status_code == 429


async def test_password_spraying_from_one_ip_is_limited(client):
    for i in range(100):
        assert (await _login(client, f"user{i}@example.com", "Spring2026")).status_code == 400
    assert (await _login(client, "user-next@example.com", "Spring2026")).status_code == 429


async def test_unknown_email_failures_are_counted_too(client):
    for _ in range(5):
        await _login(client, "ghost@example.com", "x")
    assert (await _login(client, "ghost@example.com", "x")).status_code == 429


async def test_reset_unlocks_account(client, outbox, test_user_factory):
    await test_user_factory("locked@example.com", "old-password")
    for _ in range(5):
        await _login(client, "locked@example.com", "wrong")
    assert (await _login(client, "locked@example.com", "old-password")).status_code == 429

    await client.post(FORGOT, json={"email": "locked@example.com"})
    await client.post(RESET, json={"token": _token(outbox[0], "/reset-password"), "password": "new-password"})
    assert (await _login(client, "locked@example.com", "new-password")).status_code == 200


async def test_inactive_account_with_right_password_is_not_a_failure(client, test_user_factory):
    await test_user_factory("waiting@example.com", "password123", is_active=False)
    for _ in range(6):
        assert (await _login(client, "waiting@example.com", "password123")).status_code == 403


async def test_register_is_limited_per_ip(client):
    for i in range(10):
        await _register(client, email=f"bulk{i}@example.com")
    r = await client.post("/api/v1/auth/register", json={"email": "bulk-x@example.com", "password": "password123", "full_name": "X"})
    assert r.status_code == 429


async def test_redis_outage_fails_open(client, test_user_factory, monkeypatch, caplog):
    await test_user_factory("ok@example.com", "password123")

    class Down:
        def __getattr__(self, name):
            raise ConnectionError("redis down")

    monkeypatch.setattr(throttle, "_redis", lambda: Down())
    with caplog.at_level(logging.WARNING, logger="app.core.throttle"):
        for _ in range(7):
            await _login(client, "ok@example.com", "wrong")
        assert (await _login(client, "ok@example.com", "password123")).status_code == 200
    assert "throttle" in caplog.text


# ── Xat backend'i ────────────────────────────────────────────────────


async def test_mail_backend_selection(monkeypatch, caplog):
    mail = mailer.Mail(to="a@example.com", subject="S", body="havola: http://x/verify-email#token=abc")

    monkeypatch.setattr(settings, "MAIL_BACKEND", "")
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    assert mailer.backend() == "off" and not mailer.enabled()
    assert await mailer.send([mail]) == [False]
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")
    assert mailer.backend() == "smtp"

    monkeypatch.setattr(settings, "MAIL_BACKEND", "console")
    with caplog.at_level(logging.WARNING, logger="app.notifications.mailer"):
        assert await mailer.send([mail]) == [True]
    assert "a@example.com" in caplog.text and "verify-email#token=abc" in caplog.text


async def test_account_mail_failure_is_logged_not_raised(monkeypatch, caplog):
    async def broken(mails):
        raise OSError("connection refused")

    monkeypatch.setattr(settings, "MAIL_BACKEND", "smtp")
    monkeypatch.setattr(mailer, "send", broken)
    user = User(email="a@example.com", full_name="A")
    with caplog.at_level(logging.ERROR, logger="app.core.account"):
        await account.deliver(account.compose(user, Purpose.RESET_PASSWORD, "tok"))
    assert "connection refused" in caplog.text


async def test_legacy_token_without_iat_rejected_after_password_change(client, test_user_factory, db_session):
    from jose import jwt

    user = await test_user_factory("legacy@example.com", "password123")
    legacy = jwt.encode(
        {"sub": str(user.id), "token_type": "access", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        settings.SECRET_KEY, algorithm=settings.ALGORITHM,
    )
    assert (await client.get(ME, headers=_bearer(legacy))).status_code == 200    # parol hali almashmagan
    user.password_changed_at = datetime.now(timezone.utc)
    await db_session.commit()
    assert (await client.get(ME, headers=_bearer(legacy))).status_code == 401
