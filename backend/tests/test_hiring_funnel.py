"""
Ishga olish voronkasi (CONTRACT.md §27): ariza → sinov → suhbat → taklif → qabul.

Asosiy qoidalar: kogorta — davr ichida berilgan arizalar; bosqich ixtiyoriy,
`step_rate` oldingi bosqichga yetganlar ichida; qaytarib olingan ariza faqat
son sifatida (CSV'da yo'q); email faqat taklif qabul qilinganda; boshqa
kompaniya ma'lumoti ko'rinmaydi.
"""
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import update

from app.api import talent_hunt as talent_api
from app.api import vacancies as vacancies_api
from app.models.enums import (
    ApplicationInterviewOutcome, ApplicationInterviewStatus, ApplicationStatus, AssessmentStatus, OfferResponse,
    RunStatus, TalentOfferStatus, VacancyStatus,
)
from app.models.talent import ApplicationAssessment, ApplicationInterview, TalentOffer, Vacancy, VacancyApplication
from app.talent import assessments, hiring
from tests.test_application_interviews import T0, TASHKENT, _apply, _base, _proposal, _slot
from tests.test_company_report import _rows
from tests.test_vacancies import BODY, _no_expire, _open_vacancy, world  # noqa: F401 — fixture'lar


@pytest.fixture
def clock(monkeypatch):
    now = [T0]
    monkeypatch.setattr(vacancies_api, "_now", lambda: now[0])
    monkeypatch.setattr(talent_api, "_now", lambda: now[0])
    return now


REPORT = "/api/v1/company/vacancies/report"


async def _report(client, headers, **params):
    r = await client.get(REPORT, headers=headers, params=params)
    assert r.status_code == 200, r.text
    return r.json()


# ── API: to'liq oqim ─────────────────────────────────────────────────


async def test_funnel_end_to_end(client, db_session, world, clock):
    w = world
    vid = (await _open_vacancy(client, w))["id"]
    strong_app = await _apply(client, w.strong_h, vid)
    clock[0] = T0 + timedelta(hours=2)
    weak_app = await _apply(client, w.weak_h, vid)
    shy_app = await _apply(client, w.shy_h, vid)

    # Dilnoza: suhbat (o'tdi) → taklif → qabul
    clock[0] = T0 + timedelta(hours=6)
    interview = (await client.post(_base(vid, strong_app), headers=w.alpha_h, json=_proposal(26))).json()
    await client.post(_base(vid, shy_app), headers=w.alpha_h, json=_proposal(72))
    await client.post(f"/api/v1/vacancies/{vid}/interviews/{interview['id']}/confirm", headers=w.strong_h,
                      json={"starts_at": _slot(26).astimezone(TASHKENT).isoformat()})
    clock[0] = _slot(27)
    r = await client.post(f"{_base(vid, strong_app)}/{interview['id']}/outcome", headers=w.alpha_h, json={"outcome": "passed"})
    assert r.status_code == 200, r.text
    offer = await client.post("/api/v1/talents/offers", headers=w.alpha_h, json={
        "candidate_user_id": str(w.strong.id), "position_title": BODY["title"],
        "message": "Jamoamizga taklif qilamiz.", "vacancy_id": vid,
    })
    assert offer.status_code == 201, offer.text
    clock[0] = _slot(48)
    r = await client.post(f"/api/v1/talents/offers/{offer.json()['id']}/respond", headers=w.strong_h,
                          json={"decision": "accepted"})
    assert r.status_code == 200, r.text

    # Bekzod: hech qanday qadamsiz rad; Malika: suhbatga chaqirilgan, keyin qaytarib oldi
    assert (await client.post(f"/api/v1/company/vacancies/{vid}/applications/{weak_app}/reject",
                              headers=w.alpha_h)).status_code == 200
    assert (await client.post(f"/api/v1/vacancies/{vid}/withdraw", headers=w.shy_h)).status_code == 200

    rep = await _report(client, w.alpha_h)
    assert rep["days"] is None and rep["vacancy_id"] is None
    assert [v["id"] for v in rep["vacancies"]] == [vid]
    assert {s["stage"]: (s["count"], s["rate"], s["step_rate"]) for s in rep["stages"]} == {
        "applied": (3, 100.0, None),
        "assessment": (0, 0.0, 0.0),
        "interview": (2, 66.7, None),        # sinovga hech kim yetmagan — maxraj 0
        "offer": (1, 33.3, 50.0),            # suhbatdagilarning yarmi taklif oldi
        "hired": (1, 33.3, 100.0),
    }
    assert rep["outcomes"] == {
        "hired": 1, "offer_pending": 0, "offer_declined": 0, "rejected": 1, "withdrawn": 1,
        "in_progress": 0, "waiting": 0, "stale": 0,
    }
    assert rep["dropoff"] == [
        {"stage": "applied", "rejected": 1, "withdrawn": 0},
        {"stage": "assessment", "rejected": 0, "withdrawn": 0},
        {"stage": "interview", "rejected": 0, "withdrawn": 1},
    ]
    assert rep["interviews"] == {
        "proposed": 2, "confirmed": 1, "declined": 0, "held": 1, "passed": 1, "failed": 0, "no_show": 0,
        "pass_rate": 100.0, "show_rate": 100.0,
    }
    assert rep["assessments"]["sent"] == 0 and rep["assessments"]["completion_rate"] is None
    # Dilnoza: 6 soatda birinchi qadam, 27 soatda taklif, 48 soatda qabul; Malika: 4 soatda suhbat taklifi
    assert rep["timing"] == {"first_action_hours": 5.0, "offer_days": 1.1, "hire_days": 2.0}
    assert rep["by_vacancy"] == [{
        "vacancy_id": vid, "title": BODY["title"], "status": "open",
        "applied": 3, "assessment": 0, "interview": 2, "offer": 1, "hired": 1, "hire_rate": 33.3,
    }]

    # CSV: qaytarib olgan Malika yo'q, email faqat qabul qilgan Dilnozada
    res = await client.get(f"{REPORT}/applications.csv", headers=w.alpha_h)
    assert res.status_code == 200 and "attachment" in res.headers["content-disposition"]
    header, *rows = _rows(res)
    assert header[-1] == "candidate_email"
    got = {row[2]: dict(zip(header, row)) for row in rows}
    assert set(got) == {"Dilnoza Karimova", "Bekzod Aliyev"}
    assert got["Dilnoza Karimova"]["furthest_stage"] == "hired"
    assert got["Dilnoza Karimova"]["offer_status"] == "accepted"
    assert got["Dilnoza Karimova"]["interviews_held"] == "1"
    assert got["Dilnoza Karimova"]["candidate_email"] == "strong@test.uz"
    assert got["Dilnoza Karimova"]["hired_at"] == _slot(48).astimezone(TASHKENT).strftime("%Y-%m-%d %H:%M")
    assert got["Bekzod Aliyev"]["status"] == "rejected" and got["Bekzod Aliyev"]["candidate_email"] == ""


async def test_scope_period_and_access(client, db_session, world, clock):
    w = world
    vid = (await _open_vacancy(client, w))["id"]
    other = (await _open_vacancy(client, w, title="Data analitik"))["id"]
    old_app = await _apply(client, w.strong_h, vid)
    await _apply(client, w.weak_h, other)
    await _apply(client, w.shy_h, vid)
    # Dilnoza arizasi 40 kun oldin — 30 kunlik kogortaga kirmaydi
    await db_session.execute(
        update(VacancyApplication).where(VacancyApplication.id == uuid.UUID(old_app))
        .values(created_at=T0 - timedelta(days=40), updated_at=T0 - timedelta(days=40))
    )
    await db_session.commit()

    full = await _report(client, w.alpha_h)
    assert full["stages"][0]["count"] == 3
    assert full["outcomes"]["waiting"] == 3 and full["outcomes"]["stale"] == 1     # 7 kundan ko'p javobsiz
    assert [r["title"] for r in full["by_vacancy"]] == [BODY["title"], "Data analitik"]
    assert (await _report(client, w.alpha_h, days=30))["stages"][0]["count"] == 2
    only = await _report(client, w.alpha_h, vacancy_id=other)
    assert only["vacancy_id"] == other and only["stages"][0]["count"] == 1
    assert [r["vacancy_id"] for r in only["by_vacancy"]] == [other]
    assert len(only["vacancies"]) == 2           # tanlov uchun hammasi

    # qoralama tanlovda yo'q; boshqa kompaniya — bo'sh, uning vakansiyasi bilan — 404
    await client.post("/api/v1/company/vacancies", headers=w.alpha_h, json=BODY)
    assert len((await _report(client, w.alpha_h))["vacancies"]) == 2
    beta = await _report(client, w.beta_h)
    assert beta["stages"][0] == {"stage": "applied", "count": 0, "rate": None, "step_rate": None}
    assert beta["by_vacancy"] == [] and beta["vacancies"] == []
    for path in (REPORT, f"{REPORT}/applications.csv"):
        assert (await client.get(path, headers=w.beta_h, params={"vacancy_id": vid})).status_code == 404
        assert (await client.get(path, headers=w.strong_h)).status_code == 403
        assert (await client.get(path)).status_code == 401
        assert (await client.get(path, headers=w.alpha_h, params={"days": 0})).status_code == 422
    _, *beta_rows = _rows(await client.get(f"{REPORT}/applications.csv", headers=w.beta_h))
    assert beta_rows == []


# ── Sof funksiyalar: sinov, taklif holatlari, bosqich tartibi ────────


def _track(status=ApplicationStatus.APPLIED, *, applied=T0, tests=(), interviews=(), offers=()):
    vacancy = Vacancy(id=uuid.uuid4(), title="Backend", status=VacancyStatus.OPEN)
    app = VacancyApplication(id=uuid.uuid4(), status=status, created_at=applied, updated_at=applied)
    return hiring.Track(app, vacancy, list(tests), list(interviews), list(offers))


def _test(status, *, created, run_status=None, score=None, reported=True):
    run = None
    if run_status is not None:
        run = SimpleNamespace(status=run_status, competency_scores={},
                              final_report={"overall_score": score} if reported else None)
    a = ApplicationAssessment(status=status, created_at=created, start_by=created + timedelta(days=5))
    return assessments.Item(a, SimpleNamespace(title="Sinov"), run)


def _offer(created, status=TalentOfferStatus.SENT, response=None):
    return TalentOffer(created_at=created, status=status, response=response,
                       responded_at=created + timedelta(days=1) if response else None)


def test_assessment_stats_and_outcomes():
    h = timedelta(hours=1)
    done = _test(AssessmentStatus.STARTED, created=T0 + 3 * h, run_status=RunStatus.COMPLETED, score=80.0)
    expired = _test(AssessmentStatus.STARTED, created=T0 + 3 * h, run_status=RunStatus.EXPIRED, score=40.0)
    running = _test(AssessmentStatus.STARTED, created=T0 + h, run_status=RunStatus.ACTIVE)
    scoring = _test(AssessmentStatus.STARTED, created=T0 + h, run_status=RunStatus.COMPLETED, reported=False)
    cancelled = _test(AssessmentStatus.CANCELLED, created=T0 + h)
    tracks = [
        _track(ApplicationStatus.OFFERED, tests=[done], offers=[_offer(T0 + 50 * h)]),
        _track(ApplicationStatus.OFFERED, tests=[expired],
               offers=[_offer(T0 + 10 * h, TalentOfferStatus.RESPONDED, OfferResponse.DECLINED)]),
        _track(ApplicationStatus.INTERVIEWING, tests=[running]),
        _track(ApplicationStatus.REJECTED, tests=[scoring]),
        _track(ApplicationStatus.WITHDRAWN, tests=[cancelled]),
        # suhbatsiz, sinovsiz to'g'ridan-to'g'ri taklif — bosqichlar ixtiyoriy
        _track(ApplicationStatus.OFFERED, offers=[_offer(T0 + 2 * h, TalentOfferStatus.RESPONDED, OfferResponse.ACCEPTED)]),
    ]
    now = T0 + timedelta(days=3)
    assert hiring.assessment_stats(tracks, now) == {
        "sent": 5, "started": 4, "completed": 2, "cancelled": 1, "completion_rate": 50.0, "avg_score": 60.0,
    }
    assert [t.outcome() for t in tracks] == [
        "offer_pending", "offer_declined", "in_progress", "rejected", "withdrawn", "hired",
    ]
    assert [t.furthest() for t in tracks] == ["offer", "offer", "assessment", "assessment", "assessment", "hired"]
    assert hiring.dropoff(tracks)[1] == {"stage": "assessment", "rejected": 1, "withdrawn": 1}
    stages = {s["stage"]: s for s in hiring.stages(tracks)}
    assert stages["assessment"]["count"] == 5 and stages["interview"]["count"] == 0
    assert stages["offer"]["step_rate"] is None          # suhbatga hech kim yetmagan
    assert stages["hired"]["step_rate"] == 33.3
    # birinchi qadam: 3, 3, 1, 1, 1 va 2 soat → median 1.5; taklifgacha 50/24, 10/24, 2/24 kun
    assert hiring.timing(tracks) == {"first_action_hours": 1.5, "offer_days": 0.4, "hire_days": 1.1}


def test_interview_stats():
    def iv(status, outcome=None, confirmed=True):
        return ApplicationInterview(status=status, outcome=outcome, created_at=T0,
                                    confirmed_at=T0 if confirmed else None)
    track = _track(ApplicationStatus.INTERVIEWING, interviews=[
        iv(ApplicationInterviewStatus.COMPLETED, ApplicationInterviewOutcome.PASSED),
        iv(ApplicationInterviewStatus.COMPLETED, ApplicationInterviewOutcome.FAILED),
        iv(ApplicationInterviewStatus.COMPLETED, ApplicationInterviewOutcome.NO_SHOW),
        iv(ApplicationInterviewStatus.DECLINED, confirmed=False),
        iv(ApplicationInterviewStatus.PROPOSED, confirmed=False),
    ])
    assert hiring.interview_stats([track]) == {
        "proposed": 5, "confirmed": 3, "declined": 1, "held": 2, "passed": 1, "failed": 1, "no_show": 1,
        "pass_rate": 50.0, "show_rate": 66.7,
    }
