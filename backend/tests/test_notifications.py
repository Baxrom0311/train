"""
Bildirishnomalar (CONTRACT.md §15): manbalar, takrorlanmaslik, dedlayn
eslatmasi, email cron'i va API.
"""
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.models.notification import Notification, NotificationSettings
from app.notifications import emails
from app.notifications.kinds import Kind
from app.notifications.run_events import deadline_reminders, from_notes
from app.notifications.service import notify
from app.scenario import mentor
from app.scenario.engine import Answer, advance, submit_answer
from app.scenario.reports import write_final_report
from tests.test_runs_engine import T, _events, setup  # noqa: F401
from tests.test_runs_mentor import _graded, _no_spoiler, _reviewer
from tests.test_runs_reports import _completed_run, _summarizers
from tests.test_talent_hunt import _headers, _offer, world  # noqa: F401


@pytest.fixture(autouse=True)
def _no_expire(db_session):
    db_session.sync_session.expire_on_commit = False


async def _mine(db, user_id, kind: Kind | None = None) -> list[Notification]:
    stmt = select(Notification).where(Notification.user_id == user_id).order_by(Notification.created_at)
    if kind is not None:
        stmt = stmt.where(Notification.kind == kind.value)
    return list((await db.execute(stmt)).scalars().all())


# ── Run manbalari ────────────────────────────────────────────────────


async def test_delivered_tasks_notify_once(db_session, setup):  # noqa: F811
    run, _ = await setup(T("09:00"))
    for at in ("09:00", "09:30", "09:30"):   # cron takrorlansa ham bittadan
        await from_notes(db_session, await advance(db_session, T(at)), T(at))
        await db_session.commit()

    items = await _mine(db_session, run.user_id, Kind.TASK_DELIVERED)
    # welcome — message, bildirishnoma yo'q; standup va bug_orders — task
    assert [n.params["node_id"] for n in items] == ["standup", "bug_orders"]
    bug = items[1]
    assert bug.params["title"].startswith("Ticket ORD-142") and bug.params["type"] == "task"
    assert bug.link == f"/runs/{run.id}?event=bug_orders" and bug.params["due_at"]


async def test_deadline_reminder_once_and_only_when_unsubmitted(db_session, setup):  # noqa: F811
    run, _ = await setup(T("09:00"))
    await advance(db_session, T("09:30"))
    await db_session.commit()
    events = await _events(db_session, run)
    due = events["bug_orders"].due_at

    assert await deadline_reminders(db_session, due - timedelta(minutes=45)) == 0
    # standup (09:00 + 30 daq) va bug_orders oynasi har xil — faqat oynaga kirgani
    assert await deadline_reminders(db_session, due - timedelta(minutes=20)) == 1
    assert await deadline_reminders(db_session, due - timedelta(minutes=10)) == 0
    await db_session.commit()
    [n] = await _mine(db_session, run.user_id, Kind.DEADLINE_SOON)
    assert n.params["node_id"] == "bug_orders" and n.params["due_at"] == due.isoformat()

    # topshirilgan hodisa uchun eslatma yo'q
    run2, _ = await setup(T("09:00", day=8))
    await advance(db_session, T("09:30", day=8))
    await submit_answer(db_session, run2, "bug_orders", Answer(text="fix"), T("09:40", day=8))
    await db_session.commit()
    due2 = (await _events(db_session, run2))["bug_orders"].due_at
    await deadline_reminders(db_session, due2 - timedelta(minutes=5))
    assert not [n for n in await _mine(db_session, run2.user_id, Kind.DEADLINE_SOON) if n.params["node_id"] == "bug_orders"]


async def test_mentor_review_notifies(db_session, setup):  # noqa: F811
    run, _ = await setup(T("09:00"))
    await advance(db_session, T("09:30"))
    await db_session.commit()
    sub = await _graded(db_session, run)
    review, _ = _reviewer()
    await mentor.post_review(db_session, sub.id, T("10:01"), review_fn=review, spoiler_fn=_no_spoiler)
    await mentor.post_review(db_session, sub.id, T("10:02"), review_fn=review, spoiler_fn=_no_spoiler)

    [n] = await _mine(db_session, run.user_id, Kind.MENTOR_REVIEW)
    assert n.params["node_id"] == "bug_orders" and n.params["mentor"] and n.dedupe_key == f"review:{sub.id}"


async def test_final_report_notifies_with_certificate_code(db_session, setup):  # noqa: F811
    run = await _completed_run(db_session, setup)
    _, final, _ = _summarizers()
    assert await write_final_report(db_session, run.id, T("17:41"), summarize=final)

    [n] = await _mine(db_session, run.user_id, Kind.REPORT_READY)
    assert n.params["certificate"] is True and n.params["code"].startswith("TJ-")
    assert n.link == f"/runs/{run.id}/report" and n.params["scenario_title"]


# ── Takliflar ────────────────────────────────────────────────────────


async def test_offer_and_response_notify(client, db_session, world, test_user_factory):  # noqa: F811
    offer = (await _offer(client, world)).json()
    [received] = await _mine(db_session, world["cand"].id, Kind.OFFER_RECEIVED)
    assert received.params == {"offer_id": offer["id"], "company": "Alpha", "position": "Junior Backend"}

    r = await client.post(f"/api/v1/talents/offers/{offer['id']}/respond", headers=world["cand_h"],
                          json={"decision": "accepted"})
    assert r.status_code == 200
    staff = (await db_session.execute(
        select(Notification).where(Notification.kind == Kind.OFFER_RESPONDED.value)
    )).scalars().all()
    # faqat Alpha xodimi; Beta hech narsa olmaydi
    assert len(staff) == 1 and staff[0].params["accepted"] is True and staff[0].params["candidate"] == "Dilnoza Karimova"


# ── API ──────────────────────────────────────────────────────────────


async def test_api_lists_and_marks_read(client, db_session, world):  # noqa: F811
    me, other = world["cand"].id, None
    for i in range(3):
        await notify(db_session, me, Kind.TASK_DELIVERED, {"title": f"T{i}"}, "/runs/x", f"k{i}", at=T(f"10:0{i}"))
    await db_session.commit()
    h = world["cand_h"]

    page = (await client.get("/api/v1/users/me/notifications?limit=2", headers=h)).json()
    assert [n["params"]["title"] for n in page["items"]] == ["T2", "T1"] and page["unread"] == 3
    older = (await client.get("/api/v1/users/me/notifications", headers=h,
                              params={"before": page["items"][-1]["created_at"]})).json()
    assert [n["params"]["title"] for n in older["items"]] == ["T0"]

    r = await client.post("/api/v1/users/me/notifications/read", headers=h, json={"ids": [page["items"][0]["id"]]})
    assert r.json() == {"unread": 2}
    # boshqa foydalanuvchi meniki'ni o'qilgan qila olmaydi va ko'rmaydi
    hr = world["alpha_h"]
    await client.post("/api/v1/users/me/notifications/read", headers=hr, json={"all": True})
    assert (await client.get("/api/v1/users/me/notifications", headers=hr)).json() == {"items": [], "unread": 0}
    assert (await client.get("/api/v1/users/me/notifications/unread", headers=h)).json() == {"unread": 2}

    assert (await client.post("/api/v1/users/me/notifications/read", headers=h, json={"all": True})).json() == {"unread": 0}
    for bad in ({}, {"ids": [], "all": True}):
        assert (await client.post("/api/v1/users/me/notifications/read", headers=h, json=bad)).status_code == 422
    assert (await client.get("/api/v1/users/me/notifications")).status_code == 401
    assert other is None


async def test_settings_per_permissions(client, world):  # noqa: F811
    url = "/api/v1/users/me/notification-settings"
    student = (await client.get(url, headers=world["cand_h"])).json()
    assert student["email_enabled"] is True
    assert student["available"] == ["task_delivered", "deadline_soon", "mentor_review", "report_ready", "offer_received"]
    assert student["email_kinds"] == ["deadline_soon", "report_ready", "offer_received"]
    hr = (await client.get(url, headers=world["alpha_h"])).json()
    assert hr["available"] == ["offer_responded"] and hr["email_kinds"] == ["offer_responded"]

    r = await client.put(url, headers=world["cand_h"], json={"email_enabled": False, "email_kinds": ["mentor_review"]})
    assert r.json()["email_enabled"] is False and r.json()["email_kinds"] == ["mentor_review"]
    assert (await client.get(url, headers=world["cand_h"])).json()["email_kinds"] == ["mentor_review"]
    # talabaga kompaniya turi — 422
    assert (await client.put(url, headers=world["cand_h"],
                             json={"email_enabled": True, "email_kinds": ["offer_responded"]})).status_code == 422


# ── Email ────────────────────────────────────────────────────────────


class Outbox:
    def __init__(self, fail=False):
        self.mails, self.fail = [], fail

    async def __call__(self, mails):
        self.mails += mails
        return [not self.fail] * len(mails)


async def test_emails_respect_settings_and_age(db_session, world):  # noqa: F811
    me = world["cand"].id
    now = T("12:00")
    await notify(db_session, me, Kind.DEADLINE_SOON, {"title": "Hisobot", "due_at": T("12:30").isoformat()},
                 "/runs/r1", "a", at=now)
    await notify(db_session, me, Kind.TASK_DELIVERED, {"title": "Yangi", "due_at": None}, "/runs/r1", "b", at=now)
    await notify(db_session, me, Kind.REPORT_READY, {"scenario_title": "Eski", "code": None}, "/x", "c",
                 at=now - timedelta(hours=2))
    await db_session.commit()

    out = Outbox()
    assert await emails.send_pending(db_session, now, send=out) == {"sent": 1, "skipped": 1, "failed": 0}
    await db_session.commit()
    [mail] = out.mails
    assert mail.to == "cand@test.uz" and "Dedlayn yaqin: Hisobot" in mail.subject
    assert "12:30" in mail.body and "/runs/r1" in mail.body and "Dilnoza Karimova" in mail.body
    status = {n.dedupe_key: n.email_status for n in await _mine(db_session, me)}
    assert status == {"a": "sent", "b": "skipped", "c": "skipped"}
    # qayta ishga tushsa — hech narsa qayta yuborilmaydi
    assert await emails.send_pending(db_session, now, send=out) == {"sent": 0, "skipped": 0, "failed": 0}

    # email o'chirilgan — yuborilmaydi; o'qilgani ham
    db_session.add(NotificationSettings(user_id=me, email_enabled=False, email_kinds=["deadline_soon"]))
    await notify(db_session, me, Kind.DEADLINE_SOON, {"title": "X", "due_at": now.isoformat()}, "/runs/r2", "d", at=now)
    await db_session.commit()
    failing = Outbox(fail=True)
    assert await emails.send_pending(db_session, now, send=failing) == {"sent": 0, "skipped": 1, "failed": 0}
    assert failing.mails == []


async def test_email_failure_is_recorded(db_session, world):  # noqa: F811
    me = world["cand"].id
    await notify(db_session, me, Kind.OFFER_RECEIVED, {"company": "Alpha", "position": "Junior"}, "/offers", "o", at=T("12:00"))
    await db_session.commit()

    async def broken(mails):
        raise OSError("smtp down")

    assert await emails.send_pending(db_session, T("12:01"), send=broken) == {"sent": 0, "skipped": 0, "failed": 1}
    [n] = await _mine(db_session, me)
    assert n.email_status == "failed" and n.emailed_at is None
