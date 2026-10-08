"""
Suhbat bosqichlari (CONTRACT.md §25): kompaniya vaqt taklif qiladi, talaba
tanlaydi yoki rad etadi, kompaniya natijani belgilaydi; ariza yopilsa faol
suhbat bekor bo'ladi; ≤ 2 soat qolganda bir martalik eslatma.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.api import vacancies as vacancies_api
from app.models.enums import ApplicationInterviewStatus, ApplicationStatus
from app.models.notification import Notification
from app.models.talent import ApplicationInterview, VacancyApplication
from app.notifications.emails import render
from app.notifications.kinds import Kind, available_for
from app.notifications.meetings import interview_reminders
from tests.test_vacancies import BODY, _no_expire, _open_vacancy, world  # noqa: F401 — fixture'lar

T0 = datetime(2026, 10, 12, 6, 0, tzinfo=timezone.utc)       # dushanba, 11:00 Toshkent
TASHKENT = timezone(timedelta(hours=5))


@pytest.fixture
def clock(monkeypatch):
    now = [T0]
    monkeypatch.setattr(vacancies_api, "_now", lambda: now[0])
    return now


def _slot(hours: float) -> datetime:
    return T0 + timedelta(hours=hours)


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _proposal(*hours: float, **extra):
    return {
        "slots": [_slot(h).astimezone(TASHKENT).isoformat() for h in hours],
        "duration_minutes": 45, "format": "online", "place": "https://meet.example.uz/alpha-hr", **extra,
    }


async def _apply(client, headers, vid):
    r = await client.post(f"/api/v1/vacancies/{vid}/apply", headers=headers, json={})
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _notes(db, kind: Kind) -> list[Notification]:
    return list((await db.execute(
        select(Notification).where(Notification.kind == kind.value).order_by(Notification.created_at)
    )).scalars())


def _base(vid, app_id):
    return f"/api/v1/company/vacancies/{vid}/applications/{app_id}/interviews"


async def test_propose_confirm_remind_and_pass(client, db_session, world, clock):
    w = world
    vid = (await _open_vacancy(client, w))["id"]
    app_id = await _apply(client, w.shy_h, vid)
    base = _base(vid, app_id)

    # tekshiruv: mintaqasiz, juda yaqin, 60 kundan uzoq, takror, 4 ta variant, joy bo'sh
    naive = {**_proposal(26), "slots": ["2026-10-13T10:00:00"]}
    for bad in (naive, _proposal(0.5), _proposal(24 * 61), _proposal(26, 26), _proposal(26, 27, 28, 29),
                _proposal(26, place=" "), _proposal(26, duration_minutes=10)):
        assert (await client.post(base, headers=w.alpha_h, json=bad)).status_code == 422, bad
    assert (await client.post(base, headers=w.beta_h, json=_proposal(26))).status_code == 404
    assert (await client.post(base, headers=w.shy_h, json=_proposal(26))).status_code == 403

    r = await client.post(base, headers=w.alpha_h, json=_proposal(50, 26, note="  Python bo'yicha texnik suhbat  "))
    assert r.status_code == 201, r.text
    proposed = r.json()
    assert proposed["round"] == 1 and proposed["status"] == "proposed" and proposed["expired"] is False
    assert proposed["slots"] == [_iso(_slot(26)), _iso(_slot(50))]           # UTC, o'sish tartibida
    assert proposed["note"] == "Python bo'yicha texnik suhbat"
    assert (await client.post(base, headers=w.alpha_h, json=_proposal(30))).status_code == 409   # faol bor

    note = (await _notes(db_session, Kind.INTERVIEW_PROPOSED))[0]
    assert note.user_id == w.shy.id and note.link == f"/vacancies/{vid}"
    assert note.params["round"] == 1 and note.params["company"] == "Alpha" and len(note.params["slots"]) == 2
    assert "12.10" not in render(note)[1] and "13.10 13:00" in render(note)[1]   # Toshkent vaqti

    apps = (await client.get(f"/api/v1/company/vacancies/{vid}/applications", headers=w.alpha_h)).json()
    assert apps[0]["status"] == "interviewing" and apps[0]["interviews"][0]["id"] == proposed["id"]
    counts = (await client.get(f"/api/v1/company/vacancies/{vid}", headers=w.alpha_h)).json()["counts"]
    assert counts == {**counts, "applications": 1, "new": 0}

    # talaba: ichki izoh va muallif ko'rinmaydi
    detail = (await client.get(f"/api/v1/vacancies/{vid}", headers=w.shy_h)).json()
    assert detail["application_status"] == "interviewing"
    assert [i["id"] for i in detail["interviews"]] == [proposed["id"]]
    assert "outcome_note" not in detail["interviews"][0] and "created_by" not in detail["interviews"][0]
    mine = (await client.get("/api/v1/users/me/applications", headers=w.shy_h)).json()
    assert mine[0]["interview"]["id"] == proposed["id"]

    confirm = f"/api/v1/vacancies/{vid}/interviews/{proposed['id']}/confirm"
    assert (await client.post(confirm, headers=w.strong_h, json={"starts_at": _iso(_slot(26))})).status_code == 404
    assert (await client.post(confirm, headers=w.shy_h, json={"starts_at": _iso(_slot(27))})).status_code == 409
    assert (await client.post(confirm, headers=w.shy_h, json={"starts_at": "2026-10-13T07:00:00"})).status_code == 422
    # Toshkent ko'rinishidagi o'sha vaqt — bir xil variant
    r = await client.post(confirm, headers=w.shy_h, json={"starts_at": _slot(26).astimezone(TASHKENT).isoformat()})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "confirmed" and r.json()["starts_at"] == _iso(_slot(26))
    assert (await client.post(confirm, headers=w.shy_h, json={"starts_at": _iso(_slot(26))})).status_code == 409

    confirmed = await _notes(db_session, Kind.INTERVIEW_CONFIRMED)
    assert len(confirmed) == 1 and confirmed[0].link == f"/company/vacancies/{vid}"
    assert confirmed[0].params["candidate"] == "Malika Tosheva" and confirmed[0].params["starts_at"] == _slot(26).isoformat()

    upcoming = (await client.get("/api/v1/company/vacancies/interviews", headers=w.alpha_h)).json()
    assert [(u["id"], u["candidate_name"], u["vacancy_title"]) for u in upcoming] == [
        (proposed["id"], "Malika Tosheva", BODY["title"])]
    assert (await client.get("/api/v1/company/vacancies/interviews", headers=w.beta_h)).json() == []

    # eslatma: 2 soatdan ko'p qolganda yo'q, keyin bir marta — talaba va HR'ga
    assert await interview_reminders(db_session, _slot(23)) == 0
    assert await interview_reminders(db_session, _slot(24.5)) == 1
    await db_session.commit()
    assert await interview_reminders(db_session, _slot(25)) == 0
    reminders = await _notes(db_session, Kind.INTERVIEW_REMINDER)
    assert sorted(n.link for n in reminders) == sorted([f"/vacancies/{vid}", f"/company/vacancies/{vid}"])
    assert reminders[0].params["place"] == "https://meet.example.uz/alpha-hr"

    outcome = f"{base}/{proposed['id']}/outcome"
    assert (await client.post(outcome, headers=w.alpha_h, json={"outcome": "passed"})).status_code == 409   # hali boshlanmagan
    clock[0] = _slot(27)
    r = await client.post(outcome, headers=w.alpha_h, json={"outcome": "passed", "note": "Kuchli nomzod"})
    assert r.json()["status"] == "completed" and r.json()["outcome"] == "passed" and r.json()["outcome_note"] == "Kuchli nomzod"
    assert (await client.post(outcome, headers=w.alpha_h, json={"outcome": "failed"})).status_code == 409
    detail = (await client.get(f"/api/v1/vacancies/{vid}", headers=w.shy_h)).json()
    assert detail["application_status"] == "interviewing" and detail["interviews"][0]["outcome"] == "passed"

    # 2-bosqich, keyin taklif — faol suhbat jim bekor qilinadi
    second = (await client.post(base, headers=w.alpha_h, json=_proposal(48))).json()
    assert second["round"] == 2
    offer = {"candidate_user_id": str(w.shy.id), "position_title": BODY["title"], "message": "Jamoamizga taklif qilamiz.",
             "vacancy_id": vid}
    assert (await client.post("/api/v1/talents/offers", headers=w.alpha_h, json=offer)).status_code == 201
    assert (await db_session.get(VacancyApplication, uuid.UUID(app_id), populate_existing=True)).status == ApplicationStatus.OFFERED
    assert (await db_session.get(ApplicationInterview, uuid.UUID(second["id"]), populate_existing=True)).status == ApplicationInterviewStatus.CANCELLED
    assert await _notes(db_session, Kind.INTERVIEW_CANCELLED) == []
    assert (await client.post(base, headers=w.alpha_h, json=_proposal(50))).status_code == 409    # taklif yuborilgan
    assert (await client.get("/api/v1/company/vacancies/interviews", headers=w.alpha_h)).json() == []


async def test_decline_cancel_withdraw_and_rejection(client, db_session, world, clock):
    w = world
    vid = (await _open_vacancy(client, w))["id"]
    weak_app, shy_app, strong_app = [await _apply(client, h, vid) for h in (w.weak_h, w.shy_h, w.strong_h)]

    # talaba rad etadi (sabab bilan) — ariza suhbat bosqichida qoladi
    first = (await client.post(_base(vid, weak_app), headers=w.alpha_h, json=_proposal(26))).json()
    decline = f"/api/v1/vacancies/{vid}/interviews/{first['id']}/decline"
    assert (await client.post(decline, headers=w.shy_h, json={})).status_code == 404               # boshqa talaba
    r = await client.post(decline, headers=w.weak_h, json={"reason": "  Bu kuni imtihonim bor  "})
    assert r.json()["status"] == "declined" and r.json()["decline_reason"] == "Bu kuni imtihonim bor"
    assert (await client.post(decline, headers=w.weak_h, json={})).status_code == 409
    declined = await _notes(db_session, Kind.INTERVIEW_DECLINED)
    assert len(declined) == 1 and declined[0].params["reason"] == "Bu kuni imtihonim bor" and not declined[0].params["withdrawn"]

    # yangi vaqt (bosqich o'sha), kompaniya bekor qiladi — talabaga xabar
    again = (await client.post(_base(vid, weak_app), headers=w.alpha_h, json=_proposal(30, 31, format="office",
                                                                                     place="Toshkent, Amir Temur 1"))).json()
    assert again["round"] == 1 and again["format"] == "office"
    cancel = f"{_base(vid, weak_app)}/{again['id']}/cancel"
    assert (await client.post(cancel, headers=w.beta_h)).status_code == 404
    assert (await client.post(cancel, headers=w.alpha_h)).json()["status"] == "cancelled"
    assert (await client.post(cancel, headers=w.alpha_h)).status_code == 409
    assert [n.user_id for n in await _notes(db_session, Kind.INTERVIEW_CANCELLED)] == [w.weak.id]

    # talaba arizani qaytarib oladi — faol suhbat bekor, kompaniyaga "qaytarib oldi"
    third = (await client.post(_base(vid, weak_app), headers=w.alpha_h, json=_proposal(40))).json()
    assert (await client.post(f"/api/v1/vacancies/{vid}/withdraw", headers=w.weak_h)).json()["status"] == "withdrawn"
    assert (await db_session.get(ApplicationInterview, uuid.UUID(third["id"]), populate_existing=True)).status == ApplicationInterviewStatus.CANCELLED
    withdrawn = (await _notes(db_session, Kind.INTERVIEW_DECLINED))[-1]
    assert withdrawn.params["withdrawn"] is True and "qaytarib oldi" in render(withdrawn)[1]
    confirm = f"/api/v1/vacancies/{vid}/interviews/{third['id']}/confirm"
    assert (await client.post(confirm, headers=w.weak_h, json={"starts_at": _iso(_slot(40))})).status_code == 404
    assert (await client.post(_base(vid, weak_app), headers=w.alpha_h, json=_proposal(40))).status_code == 404

    # kelmadi — ariza rad etiladi, talabaga rad xabari
    meeting = (await client.post(_base(vid, shy_app), headers=w.alpha_h, json=_proposal(26))).json()
    await client.post(f"/api/v1/vacancies/{vid}/interviews/{meeting['id']}/confirm", headers=w.shy_h,
                      json={"starts_at": _iso(_slot(26))})
    clock[0] = _slot(26)
    r = await client.post(f"{_base(vid, shy_app)}/{meeting['id']}/outcome", headers=w.alpha_h, json={"outcome": "no_show"})
    assert r.json()["outcome"] == "no_show"
    rejected = await _notes(db_session, Kind.APPLICATION_REJECTED)
    assert [n.user_id for n in rejected] == [w.shy.id]
    assert (await client.get(f"/api/v1/vacancies/{vid}", headers=w.shy_h)).json()["application_status"] == "rejected"
    assert (await client.post(_base(vid, shy_app), headers=w.alpha_h, json=_proposal(30))).status_code == 409

    # variantlari o'tib ketgan taklif — `expired`, tanlab bo'lmaydi; rad etish uni ham yopadi
    late = (await client.post(_base(vid, strong_app), headers=w.alpha_h, json=_proposal(28, 29))).json()
    clock[0] = _slot(30)
    apps = {a["id"]: a for a in (await client.get(f"/api/v1/company/vacancies/{vid}/applications", headers=w.alpha_h)).json()}
    assert apps[strong_app]["interviews"][0]["expired"] is True
    assert [a["status"] for a in apps.values()] == ["interviewing", "rejected"]          # suhbatdagilar oldin
    r = await client.post(f"/api/v1/vacancies/{vid}/interviews/{late['id']}/confirm", headers=w.strong_h,
                          json={"starts_at": _iso(_slot(29))})
    assert r.status_code == 409
    assert (await client.post(f"/api/v1/company/vacancies/{vid}/applications/{strong_app}/reject",
                              headers=w.alpha_h)).json()["status"] == "rejected"
    assert (await db_session.get(ApplicationInterview, uuid.UUID(late["id"]), populate_existing=True)).status == ApplicationInterviewStatus.CANCELLED


def test_kinds_and_email_texts():
    student, hr = available_for({"receive_offers"}), available_for({"view_candidates", "manage_vacancies"})
    assert {Kind.INTERVIEW_PROPOSED, Kind.INTERVIEW_CANCELLED, Kind.INTERVIEW_REMINDER} <= set(student)
    assert {Kind.INTERVIEW_CONFIRMED, Kind.INTERVIEW_DECLINED, Kind.INTERVIEW_REMINDER} <= set(hr)
    assert len(available_for({"receive_offers", "manage_vacancies"})) == len(set(available_for({"receive_offers", "manage_vacancies"})))

    common = {"vacancy_id": "v", "vacancy": "Analitik", "company": "Alpha", "candidate": "Malika"}
    cases = {
        Kind.INTERVIEW_CANCELLED: {**common, "starts_at": _slot(26).isoformat()},
        Kind.INTERVIEW_CONFIRMED: {**common, "starts_at": _slot(26).isoformat()},
        Kind.INTERVIEW_DECLINED: {**common, "reason": None, "withdrawn": False},
        Kind.INTERVIEW_REMINDER: {**common, "starts_at": _slot(26).isoformat(), "format": "office", "place": "Ofis"},
    }
    for kind, params in cases.items():
        subject, lead = render(Notification(kind=kind.value, params=params, link="/x"))
        assert "Analitik" in subject and lead
    assert "13.10 13:00" in render(Notification(kind="interview_confirmed", params=cases[Kind.INTERVIEW_CONFIRMED], link="/"))[1]
