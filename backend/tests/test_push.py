"""
Push bildirishnomalar (CONTRACT.md §22): obuna API, yuborish cron'i va
haqiqiy Web Push shifrlashi (pywebpush → http_ece bilan ochib tekshiriladi).
"""
import base64
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from sqlalchemy import select

from app.config import settings
from app.models.notification import Notification, NotificationSettings, PushSubscription
from app.notifications import push
from app.notifications.kinds import Kind
from app.notifications.service import notify
from tests.test_talent_hunt import _headers

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from gen_vapid_keys import generate  # noqa: E402

NOW = datetime(2026, 10, 7, 10, 0, tzinfo=timezone.utc)
KEYS = {"p256dh": "B" + "x" * 86, "auth": "a" * 22}


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


@pytest.fixture
def vapid(monkeypatch):
    public, private = generate()
    monkeypatch.setattr(settings, "VAPID_PUBLIC_KEY", public)
    monkeypatch.setattr(settings, "VAPID_PRIVATE_KEY", private)
    monkeypatch.setattr(settings, "VAPID_SUBJECT", "mailto:admin@example.uz")
    push._vapid.cache_clear()
    yield public
    push._vapid.cache_clear()


@pytest.fixture
async def student(client, test_user_factory):
    user = await test_user_factory("s@test.uz", "pass", "student")
    return user, await _headers(client, "s@test.uz")


async def _subscribe(client, headers, endpoint="https://push.example/abc"):
    return await client.post("/api/v1/users/me/push-subscriptions", headers=headers,
                             json={"endpoint": endpoint, "keys": KEYS})


async def _subs(db, user_id=None):
    stmt = select(PushSubscription).order_by(PushSubscription.created_at)
    if user_id:
        stmt = stmt.where(PushSubscription.user_id == user_id)
    return (await db.execute(stmt)).scalars().all()


# ── Sozlama va obuna API ─────────────────────────────────────────────


async def test_config_reflects_env(client, vapid):
    assert (await client.get("/api/v1/push/config")).json() == {"enabled": True, "public_key": vapid}


async def test_disabled_server_refuses_subscription(client, student):
    assert (await client.get("/api/v1/push/config")).json() == {"enabled": False, "public_key": None}
    assert (await _subscribe(client, student[1])).status_code == 409


async def test_subscribe_moves_trims_and_deletes(client, db_session, test_user_factory, student, vapid):
    user, headers = student
    user_id = user.id
    assert (await client.post("/api/v1/users/me/push-subscriptions", json={"endpoint": "x", "keys": KEYS})).status_code == 401
    bad = await client.post("/api/v1/users/me/push-subscriptions", headers=headers,
                            json={"endpoint": "http://push.example/a", "keys": KEYS})
    assert bad.status_code == 422

    assert (await _subscribe(client, headers)).status_code == 204
    assert (await _subscribe(client, headers)).status_code == 204          # takror — bitta qator
    assert [s.endpoint for s in await _subs(db_session)] == ["https://push.example/abc"]

    # shu brauzerda boshqa akkaunt — obuna yangi egaga o'tadi
    other_id = (await test_user_factory("o@test.uz", "pass", "student")).id
    other_h = await _headers(client, "o@test.uz")
    await _subscribe(client, other_h)
    db_session.expire_all()
    assert [s.user_id for s in await _subs(db_session)] == [other_id]

    # 10 tadan oshsa eng eskisi o'chadi
    for i in range(11):
        await _subscribe(client, headers, f"https://push.example/{i}")
    db_session.expire_all()
    mine = [s.endpoint for s in await _subs(db_session, user_id)]
    assert len(mine) == 10 and "https://push.example/0" not in mine

    # boshqaning obunasini o'chirib bo'lmaydi (lekin 204 — oshkor qilinmaydi)
    r = await client.request("DELETE", "/api/v1/users/me/push-subscriptions", headers=headers,
                             json={"endpoint": "https://push.example/abc"})
    assert r.status_code == 204
    db_session.expire_all()
    assert len(await _subs(db_session, other_id)) == 1
    await client.request("DELETE", "/api/v1/users/me/push-subscriptions", headers=headers,
                         json={"endpoint": "https://push.example/5"})
    db_session.expire_all()
    assert len(await _subs(db_session, user_id)) == 9


async def test_push_enabled_setting(client, student):
    headers = student[1]
    current = (await client.get("/api/v1/users/me/notification-settings", headers=headers)).json()
    assert current["push_enabled"] is True
    body = {"email_enabled": True, "email_kinds": current["email_kinds"], "push_enabled": False}
    assert (await client.put("/api/v1/users/me/notification-settings", headers=headers, json=body)).json()["push_enabled"] is False
    assert (await client.get("/api/v1/users/me/notification-settings", headers=headers)).json()["push_enabled"] is False


# ── Yuborish ─────────────────────────────────────────────────────────


async def test_send_pending(db_session, test_user_factory, vapid):
    a = await test_user_factory("a@test.uz", "pass", "student")
    b = await test_user_factory("b@test.uz", "pass", "student")
    c = await test_user_factory("c@test.uz", "pass", "student")
    d = await test_user_factory("d@test.uz", "pass", "student")
    db_session.add_all([
        PushSubscription(user_id=a.id, endpoint="https://p/a1", p256dh="k", auth="x", created_at=NOW),
        PushSubscription(user_id=a.id, endpoint="https://p/a-gone", p256dh="k", auth="x", created_at=NOW),
        PushSubscription(user_id=b.id, endpoint="https://p/b-down", p256dh="k", auth="x", created_at=NOW),
        PushSubscription(user_id=d.id, endpoint="https://p/d1", p256dh="k", auth="x", created_at=NOW),
        NotificationSettings(user_id=d.id, email_enabled=True, email_kinds=[], push_enabled=False),
    ])
    task = {"title": "LZ-214", "due_at": "2026-10-07T07:00:00+00:00", "run_id": "r", "node_id": "n"}
    await notify(db_session, a.id, Kind.TASK_DELIVERED, task, "/runs/r?event=n", "fresh", at=NOW - timedelta(minutes=1))
    await notify(db_session, a.id, Kind.TASK_DELIVERED, task, "/runs/r?event=old", "old", at=NOW - timedelta(minutes=11))
    await notify(db_session, a.id, Kind.TASK_DELIVERED, task, "/runs/r?event=read", "read", at=NOW)
    await notify(db_session, b.id, Kind.TASK_DELIVERED, task, "/runs/r", "b", at=NOW)
    await notify(db_session, c.id, Kind.TASK_DELIVERED, task, "/runs/r", "c", at=NOW)        # obuna yo'q
    await notify(db_session, d.id, Kind.TASK_DELIVERED, task, "/runs/r", "d", at=NOW)        # push o'chiq
    await db_session.commit()
    read = (await db_session.execute(select(Notification).where(Notification.dedupe_key == "read"))).scalar_one()
    read.read_at = NOW
    await db_session.commit()

    sent = []

    async def fake_send(target, data):
        sent.append((target.endpoint, json.loads(data)))
        return {"https://p/a1": None, "https://p/a-gone": 410}.get(target.endpoint, 503)

    counts = await push.send_pending(db_session, NOW, send=fake_send)
    await db_session.commit()
    # "old" yoshi bo'yicha alohida yopiladi — hisobda faqat ko'rib chiqilganlar
    assert counts == {"sent": 1, "skipped": 3, "failed": 1, "removed": 1}

    endpoints = sorted(e for e, _ in sent)
    assert endpoints == ["https://p/a-gone", "https://p/a1", "https://p/b-down"]
    payload = next(p for e, p in sent if e == "https://p/a1")
    assert payload["title"] == "Yangi vazifa: LZ-214" and payload["link"] == "/runs/r?event=n"
    assert "12:00" in payload["body"]                                    # Toshkent vaqti

    db_session.expire_all()
    status = {n.dedupe_key: n.push_status for n in (await db_session.execute(select(Notification))).scalars()}
    assert status == {"fresh": "sent", "old": "skipped", "read": "skipped", "b": "failed", "c": "skipped", "d": "skipped"}
    subs = {s.endpoint: s for s in await _subs(db_session)}
    assert "https://p/a-gone" not in subs and subs["https://p/a1"].last_used_at == NOW
    assert subs["https://p/b-down"].last_used_at is None

    # ikkinchi marta — hech narsa qayta yuborilmaydi
    assert await push.send_pending(db_session, NOW, send=fake_send) == {"sent": 0, "skipped": 0, "failed": 0, "removed": 0}


def test_real_web_push_encryption(vapid, monkeypatch):
    """pywebpush haqiqiy shifrlaydi: brauzer kaliti bilan ochilganda payload bir xil."""
    import http_ece

    browser = ec.generate_private_key(ec.SECP256R1())
    auth = b"0123456789abcdef"
    target = push.Target(
        id=None, endpoint="https://fcm.example/send/abc",
        p256dh=_b64(browser.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)),
        auth=_b64(auth),
    )
    captured = {}

    class Resp:
        status_code, reason, text, headers = 201, "Created", "", {}

    def fake_post(url, data=None, headers=None, timeout=None, **_):
        captured.update(url=url, data=data, headers=headers)
        return Resp()

    monkeypatch.setattr(requests, "post", fake_post)
    body = json.dumps({"title": "Salom", "link": "/runs/x"})
    assert push._send_sync(target, body) is None

    assert captured["url"] == target.endpoint
    assert captured["headers"]["content-encoding"] == "aes128gcm"
    assert captured["headers"]["ttl"] == str(push.TTL_SECONDS)
    assert captured["headers"]["authorization"].startswith("vapid t=") and vapid in captured["headers"]["authorization"]
    plain = http_ece.decrypt(captured["data"], private_key=browser, auth_secret=auth, version="aes128gcm")
    assert json.loads(plain) == {"title": "Salom", "link": "/runs/x"}

    class Gone(Resp):
        status_code, reason = 410, "Gone"

    monkeypatch.setattr(requests, "post", lambda *a, **k: Gone())
    assert push._send_sync(target, body) == 410
