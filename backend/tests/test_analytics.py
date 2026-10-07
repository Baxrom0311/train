"""
Talaba analitikasi (CONTRACT.md §17).

Eng muhim qoidalar: faqat o'z tugagan Run'lari (hisobotli, bekor qilinmagan
sertifikatli); `current` — oxirgi 3 ta qiymat o'rtachasi, `delta` — birinchi
qiymatdan farq; tavsiya faqat hali tugatilmagan, fokus kompetensiyani
mashq qiladigan ssenariy.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.analytics.student import Candidate, Point, build
from app.models.credential import Certificate
from app.models.enums import RunStatus, ScenarioVersionStatus, Sector
from app.models.scenario import Run, Scenario, ScenarioVersion

NOW = datetime.now(timezone.utc)


# ── Sof hisob ────────────────────────────────────────────────────────


def _p(scores, *, overall=None, scenario=None, sector="IT", improvements=(), days_ago=0, on_time=None):
    return Point(
        run_id=uuid.uuid4(), scenario_id=scenario or uuid.uuid4(), scenario_title="S", sector=sector,
        completed_at=NOW - timedelta(days=days_ago), overall_score=overall, on_time_rate=on_time,
        competency_scores=scores, improvements=list(improvements),
    )


def _c(title, practices, scenario_id=None):
    return Candidate(
        scenario_id=scenario_id or uuid.uuid4(), title=title, sector="IT", company_name="Lazurit Go",
        duration_days=1, difficulty="junior", practices=practices,
    )


def test_empty_state():
    a = build([], in_progress=1, certificates=0, candidates=[_c("A", {"technical": 2})])
    assert a.summary == {
        "completed": 0, "in_progress": 1, "avg_score": None, "best_score": None,
        "on_time_rate": None, "certificates": 0,
    }
    assert (a.timeline, a.competencies, a.sectors, a.focus, a.improvements, a.recommendations) == ([], [], [], [], [], [])


def test_current_is_recent_mean_and_delta_from_first():
    points = [_p({"technical": v}) for v in (40.0, 50.0, 60.0, 70.0, 80.0)]
    [tech] = build(points, 0, 0, []).competencies
    assert tech["current"] == 70.0          # (60 + 70 + 80) / 3
    assert tech["trend"] == "up"
    assert tech["first"] == 40.0
    assert tech["delta"] == 30.0
    assert tech["values"] == [40.0, 50.0, 60.0, 70.0, 80.0]


def test_first_value_is_baseline_not_part_of_current():
    [c] = build([_p({"technical": 60.0}), _p({"technical": 80.0})], 0, 0, []).competencies
    assert (c["first"], c["current"], c["delta"]) == (60.0, 80.0, 20.0)


def test_single_value_has_no_delta_and_is_new():
    a = build([_p({"technical": 55.0})], 0, 0, [])
    assert a.competencies[0]["delta"] is None
    assert a.focus == [{"key": "technical", "current": 55.0, "trend": "new"}]


def test_competencies_sorted_strongest_first_and_focus_is_two_weakest():
    points = [
        _p({"technical": 90.0, "communication": 50.0, "initiative": 70.0}),
        _p({"technical": 80.0, "communication": 56.0, "initiative": 60.0, "prioritization": 75.0}),
    ]
    a = build(points, 0, 0, [])
    assert [c["key"] for c in a.competencies] == ["technical", "prioritization", "initiative", "communication"]
    assert a.focus == [
        {"key": "communication", "current": 56.0, "trend": "up"},
        {"key": "initiative", "current": 60.0, "trend": "down"},
    ]


@pytest.mark.parametrize(("values", "trend"), [
    ([50.0, 53.0], "flat"),        # ±3 ichida (chegara ham)
    ([50.0, 54.0], "up"),
    ([50.0, 46.0], "down"),
    ([90.0, 40.0, 60.0, 92.0], "down"),   # oxirgi 3 tasi o'rtachasi 64 — oxirgi bitta emas
])
def test_trend_threshold(values, trend):
    [f] = build([_p({"technical": v}) for v in values], 0, 0, []).focus
    assert f["trend"] == trend


def test_summary_and_sectors():
    points = [
        _p({}, overall=60.0, sector="IT", on_time=100.0, days_ago=3),
        _p({}, overall=None, sector="Banking", on_time=None, days_ago=2),
        _p({}, overall=90.0, sector="IT", on_time=50.0, days_ago=1),
    ]
    a = build(points, in_progress=2, certificates=1, candidates=[])
    assert a.summary == {
        "completed": 3, "in_progress": 2, "avg_score": 75.0, "best_score": 90.0,
        "on_time_rate": 75.0, "certificates": 1,
    }
    assert a.sectors == [
        {"sector": "IT", "runs": 2, "avg_score": 75.0},
        {"sector": "Banking", "runs": 1, "avg_score": None},
    ]


def test_improvements_come_from_last_run_only():
    points = [
        _p({}, improvements=["eski"]),
        _p({}, improvements=["a", "b", "c", "d", "e"]),
    ]
    assert build(points, 0, 0, []).improvements == ["a", "b", "c", "d"]


def test_recommendations_rank_by_focus_practice_and_skip_done():
    done = uuid.uuid4()
    points = [_p({"technical": 90.0, "communication": 40.0, "initiative": 50.0}, scenario=done)]
    candidates = [
        _c("Bajarilgan", {"communication": 9}, scenario_id=done),
        _c("Faqat texnik", {"technical": 5}),                    # fokusda emas
        _c("Bitta", {"communication": 1}),
        _c("Ko'p", {"communication": 2, "initiative": 2, "technical": 4}),
        _c("Teng A", {"initiative": 1}),
        _c("Teng B", {"communication": 1, "technical": 1}),
    ]
    recs = build(points, 0, 0, candidates).recommendations
    assert [r["title"] for r in recs] == ["Ko'p", "Bitta", "Teng A"]
    # faqat fokus kompetensiyalar ko'rsatiladi
    assert recs[0]["practices"] == {"communication": 2, "initiative": 2}


# ── API ──────────────────────────────────────────────────────────────


def _definition(slug, competencies):
    return {
        "slug": slug, "title": slug, "sector": "IT", "company_name": "Lazurit Go", "duration_days": 1,
        "personas": [{"key": "lead", "name": "Lola", "role": "Lead"}],
        "nodes": [
            {"id": "t1", "type": "task", "day": 1, "at": "09:00", "from": "lead", "brief": "Yozing",
             "answer_types": ["text"], "due_in_minutes": 30, "competencies": competencies},
            {"id": "end", "type": "day_end", "day": 1, "at": "17:30"},
        ],
    }


async def _scenario(db, slug, competencies, *, sector=Sector.IT, active=True, status=ScenarioVersionStatus.PUBLISHED):
    scenario = Scenario(
        slug=slug, title=f"{slug} title", sector=sector, company_name="Lazurit Go",
        difficulty="junior", duration_days=1, is_active=active,
    )
    version = ScenarioVersion(scenario=scenario, version=1, status=status, definition=_definition(slug, competencies))
    db.add_all([scenario, version])
    await db.commit()
    return version


async def _run(db, user, version, *, score=None, competencies=None, status=RunStatus.COMPLETED,
               days_ago=1, improvements=()):
    at = NOW - timedelta(days=days_ago)
    done = status == RunStatus.COMPLETED
    run = Run(
        user_id=user.id, scenario_version_id=version.id, status=status,
        start_at=at - timedelta(hours=8), ends_at=at if done else NOW + timedelta(days=1), last_activity_at=at,
        competency_scores=competencies if done else None,
        final_report={
            "overall_score": score, "on_time_rate": 80.0, "certificate": True,
            "summary": {"summary": "Yaxshi", "strengths": [], "improvements": list(improvements)},
        } if done else None,
    )
    db.add(run)
    await db.commit()
    return run


def _certificate(run, user, *, revoked=False):
    return Certificate(
        code=uuid.uuid4().hex[:12].upper(), run_id=run.id, user_id=user.id, holder_name="Aziza",
        scenario_title="t", company_name="Lazurit Go", sector="IT", difficulty="junior",
        duration_days=1, completed_at=NOW, revoked_at=NOW if revoked else None,
    )


async def _headers(client, email):
    r = await client.post("/api/v1/auth/login", data={"username": email, "password": "pass"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(autouse=True)
def _no_expire(db_session):
    db_session.sync_session.expire_on_commit = False


@pytest.mark.asyncio
async def test_requires_auth(client):
    assert (await client.get("/api/v1/users/me/analytics")).status_code == 401


@pytest.mark.asyncio
async def test_own_runs_only_and_revoked_excluded(client, db_session, test_user_factory):
    it = await _scenario(db_session, "it-day1", ["technical"])
    bank = await _scenario(db_session, "bank-day1", ["communication"], sector=Sector.BANKING)
    soft = await _scenario(db_session, "soft-day1", ["communication", "initiative"])
    await _scenario(db_session, "hidden-day1", ["communication"], active=False)
    await _scenario(db_session, "draft-day1", ["communication"], status=ScenarioVersionStatus.DRAFT)

    me = await test_user_factory("aziza@demo.test", "pass", "student")
    other = await test_user_factory("bobur@demo.test", "pass", "student")

    first = await _run(db_session, me, it, score=60.0, competencies={"technical": 60.0, "communication": 40.0}, days_ago=5)
    await _run(db_session, me, bank, score=80.0, competencies={"technical": 80.0, "communication": 50.0},
               days_ago=2, improvements=["Qisqaroq yozing"])
    revoked = await _run(db_session, me, it, score=10.0, competencies={"technical": 10.0}, days_ago=1)
    await _run(db_session, me, soft, status=RunStatus.ACTIVE)
    await _run(db_session, other, soft, score=99.0, competencies={"communication": 99.0})
    db_session.add_all([_certificate(first, me), _certificate(revoked, me, revoked=True)])
    await db_session.commit()

    r = await client.get("/api/v1/users/me/analytics", headers=await _headers(client, "aziza@demo.test"))
    assert r.status_code == 200
    data = r.json()

    assert data["summary"] == {
        "completed": 2, "in_progress": 1, "avg_score": 70.0, "best_score": 80.0,
        "on_time_rate": 80.0, "certificates": 1,
    }
    assert [p["scenario_title"] for p in data["timeline"]] == ["it-day1 title", "bank-day1 title"]
    assert [p["overall_score"] for p in data["timeline"]] == [60.0, 80.0]
    assert {c["key"]: (c["current"], c["delta"]) for c in data["competencies"]} == {
        "technical": (80.0, 20.0), "communication": (50.0, 10.0),
    }
    assert [f["key"] for f in data["focus"]] == ["communication", "technical"]
    assert data["improvements"] == ["Qisqaroq yozing"]
    assert [s["sector"] for s in data["sectors"]] == ["Banking", "IT"]
    # bajarilgan, yashirin va qoralama ssenariylar tavsiya qilinmaydi
    assert [(x["title"], x["practices"]) for x in data["recommendations"]] == [
        ("soft-day1 title", {"communication": 1}),
    ]


@pytest.mark.asyncio
async def test_new_student_gets_empty_analytics(client, db_session, test_user_factory):
    await _scenario(db_session, "it-day1", ["technical"])
    await test_user_factory("yangi@demo.test", "pass", "student")
    data = (await client.get("/api/v1/users/me/analytics", headers=await _headers(client, "yangi@demo.test"))).json()
    assert data["summary"]["completed"] == 0
    assert data["timeline"] == data["competencies"] == data["focus"] == data["recommendations"] == []
