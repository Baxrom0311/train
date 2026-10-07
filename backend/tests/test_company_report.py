"""
Kompaniya hisoboti (CONTRACT.md §20): nomzodlar bazasi, takliflar voronkasi, CSV.

Asosiy qoidalar: bazaga faqat shu kompaniyaga ko'rinadigan nomzodlar kiradi
(yashiringanlar soni ham "oqmaydi"), takliflar — faqat kompaniyaning o'ziniki,
email CSV'da ham faqat accepted'da.
"""
import csv
import io
from datetime import datetime, timedelta, timezone

import pytest

from app.models.enums import OfferResponse, Sector, TalentOfferStatus
from app.models.talent import TalentOffer
from app.talent import report
from app.talent.profile import Profile, RunSummary
from tests.test_talent_hunt import NOW, _company, _hr, _run, _scenario, _student


def _offer(company, user, *, title="Junior Backend", status=TalentOfferStatus.SENT, response=None,
           sent_ago=timedelta(days=2), answered_after=None, due_in=timedelta(days=5)):
    created = NOW - sent_ago
    return TalentOffer(
        company_id=company.id, candidate_user_id=user.id, position_title=title,
        message="Suhbatga taklif qilamiz.", status=status, response=response,
        created_at=created, respond_due_at=created + sent_ago + due_in,
        responded_at=created + answered_after if answered_after else None,
    )


def _rows(res):
    assert res.content.startswith("﻿".encode())
    return list(csv.reader(io.StringIO(res.content.decode("utf-8-sig"))))


@pytest.fixture(autouse=True)
def _no_expire(db_session):
    db_session.sync_session.expire_on_commit = False


@pytest.fixture
async def world(client, db_session, test_user_factory):
    """Alpha'ga 2 nomzod ko'rinadi; yopiq va Alpha'dan yashiringan nomzodlar ham bor."""
    alpha = await _company(db_session, "Alpha")
    beta = await _company(db_session, "Beta")
    it = await _scenario(db_session, "it-day1")
    bank = await _scenario(db_session, "bank-day1", Sector.BANKING)
    s = test_user_factory

    dilnoza, _ = await _student(client, db_session, s, "d@test.uz", "Dilnoza Karimova", open_to_work=True)
    await _run(db_session, dilnoza, it, score=88.0, competencies={"technical": 90.0, "communication": 80.0})
    await _run(db_session, dilnoza, bank, score=76.0, competencies={"technical": 70.0}, days_ago=60)
    jasur, _ = await _student(client, db_session, s, "j@test.uz", "=HYPERLINK(\"x\")", open_to_work=True)
    await _run(db_session, jasur, it, score=55.0, competencies={"communication": 60.0}, days_ago=45)
    closed, _ = await _student(client, db_session, s, "c@test.uz", "Yopiq Nomzod", open_to_work=False)
    await _run(db_session, closed, it, score=99.0, competencies={"technical": 99.0})
    hiding, _ = await _student(client, db_session, s, "h@test.uz", "Yashirin Nomzod", open_to_work=True, hidden=[alpha.id])
    await _run(db_session, hiding, bank, score=40.0, competencies={"technical": 40.0})
    return {
        "alpha": alpha, "beta": beta, "dilnoza": dilnoza, "jasur": jasur, "closed": closed, "hiding": hiding,
        "alpha_h": await _hr(client, db_session, s, alpha, "hr@alpha.test"),
        "beta_h": await _hr(client, db_session, s, beta, "hr@beta.test"),
    }


# ── Ruxsat ───────────────────────────────────────────────────────────


async def test_only_verified_company_staff(client, db_session, test_user_factory, world):
    _, student_h = await _student(client, db_session, test_user_factory, "s@test.uz", "Talaba")
    gamma = await _company(db_session, "Gamma", verified=False)
    gamma_h = await _hr(client, db_session, test_user_factory, gamma, "hr@gamma.test")
    for path in ("/report", "/report/offers.csv", "/report/candidates.csv"):
        assert (await client.get(f"/api/v1/talents{path}", headers=student_h)).status_code == 403
        assert (await client.get(f"/api/v1/talents{path}", headers=gamma_h)).status_code == 403
        assert (await client.get(f"/api/v1/talents{path}")).status_code == 401
    assert (await client.get("/api/v1/talents/report?days=0", headers=world["alpha_h"])).status_code == 422


# ── Baza ─────────────────────────────────────────────────────────────


async def test_pool_counts_only_visible_candidates(client, world):
    pool = (await client.get("/api/v1/talents/report", headers=world["alpha_h"])).json()["pool"]
    assert pool["candidates"] == 2                       # yopiq va yashiringan kirmaydi
    assert pool["avg_score"] == round((82.0 + 55.0) / 2, 1)   # Dilnoza: (88+76)/2
    assert {b["band"]: b["candidates"] for b in pool["score_bands"]} == {
        "0-49": 0, "50-69": 1, "70-84": 1, "85-100": 0,
    }
    assert pool["sectors"] == [
        {"sector": "IT", "candidates": 2, "avg_score": 68.5},
        {"sector": "Banking", "candidates": 1, "avg_score": 82.0},
    ]
    assert pool["competencies"] == {"technical": 80.0, "communication": 70.0}

    # Beta'dan yashirinmagan — u yerda 3 ta
    beta = (await client.get("/api/v1/talents/report", headers=world["beta_h"])).json()["pool"]
    assert beta["candidates"] == 3
    assert {b["band"]: b["candidates"] for b in beta["score_bands"]}["0-49"] == 1


async def test_active_in_period_follows_days(client, world):
    get = lambda q: client.get(f"/api/v1/talents/report{q}", headers=world["alpha_h"])  # noqa: E731
    assert (await (get(""))).json()["pool"]["active_in_period"] == 2
    month = (await get("?days=30")).json()
    assert month["days"] == 30
    assert month["pool"]["active_in_period"] == 1        # Jasur 45 kun oldin tugatgan
    assert month["pool"]["candidates"] == 2              # baza — joriy holat


# ── Takliflar ────────────────────────────────────────────────────────


async def test_offer_funnel(client, db_session, world):
    a, d, j, h = world["alpha"], world["dilnoza"], world["jasur"], world["hiding"]
    db_session.add_all([
        _offer(a, d, status=TalentOfferStatus.RESPONDED, response=OfferResponse.ACCEPTED,
               sent_ago=timedelta(days=10), answered_after=timedelta(hours=5)),
        _offer(a, d, title="  junior   backend ", status=TalentOfferStatus.RESPONDED,
               response=OfferResponse.DECLINED, sent_ago=timedelta(days=5), answered_after=timedelta(hours=20)),
        _offer(a, j, title="Data Analyst", status=TalentOfferStatus.VIEWED, sent_ago=timedelta(days=3)),
        # muddati o'tgan, javobsiz; nomzod keyin yashiringan — statistika baribir qoladi
        _offer(a, h, sent_ago=timedelta(days=9), due_in=-timedelta(days=2)),
        # davrdan tashqari va boshqa kompaniyaniki
        _offer(a, j, status=TalentOfferStatus.RESPONDED, response=OfferResponse.ACCEPTED,
               sent_ago=timedelta(days=200), answered_after=timedelta(hours=1)),
        _offer(world["beta"], d, sent_ago=timedelta(days=1)),
    ])
    await db_session.commit()

    body = (await client.get("/api/v1/talents/report?days=30", headers=world["alpha_h"])).json()
    assert body["offers"] == {
        "sent": 4, "viewed": 3, "responded": 2, "accepted": 1, "declined": 1,
        "pending": 2, "overdue": 1, "response_rate": 50.0, "acceptance_rate": 50.0,
        "median_response_hours": 12.5,
    }
    assert body["by_position"] == [
        {"position_title": "Junior Backend", "sent": 3, "accepted": 1, "declined": 1, "pending": 1},
        {"position_title": "Data Analyst", "sent": 1, "accepted": 0, "declined": 0, "pending": 1},
    ]
    months = body["by_month"]
    assert sum(m["sent"] for m in months) == 4 and months[-1]["month"] == NOW.astimezone(report.TASHKENT).strftime("%Y-%m")

    everything = (await client.get("/api/v1/talents/report", headers=world["alpha_h"])).json()
    assert everything["days"] is None
    assert everything["offers"]["sent"] == 5 and everything["offers"]["accepted"] == 2
    assert sum(m["sent"] for m in everything["by_month"]) == 5


async def test_empty_report(client, db_session, test_user_factory):
    lonely = await _company(db_session, "Lonely")
    headers = await _hr(client, db_session, test_user_factory, lonely, "hr@lonely.test")
    body = (await client.get("/api/v1/talents/report", headers=headers)).json()
    assert body["company"]["name"] == "Lonely"
    assert body["pool"]["candidates"] == 0 and body["pool"]["avg_score"] is None
    assert body["offers"]["sent"] == 0
    assert body["offers"]["response_rate"] is None and body["offers"]["median_response_hours"] is None
    assert body["by_position"] == [] and body["by_month"] == []


# ── CSV ──────────────────────────────────────────────────────────────


async def test_offers_csv(client, db_session, world):
    a = world["alpha"]
    db_session.add_all([
        _offer(a, world["dilnoza"], title="-Backend", status=TalentOfferStatus.RESPONDED,
               response=OfferResponse.ACCEPTED, answered_after=timedelta(hours=3)),
        _offer(a, world["jasur"], status=TalentOfferStatus.RESPONDED,
               response=OfferResponse.DECLINED, answered_after=timedelta(hours=1)),
    ])
    await db_session.commit()

    res = await client.get("/api/v1/talents/report/offers.csv", headers=world["alpha_h"])
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")
    assert 'attachment; filename="tryjob-offers-' in res.headers["content-disposition"]
    header, *rows = _rows(res)
    assert header[-1] == "candidate_email"
    by_name = {r[2]: r for r in rows}
    accepted = by_name["Dilnoza Karimova"]
    assert accepted[1] == "'-Backend"                    # formula injection
    assert accepted[3:5] == ["responded", "accepted"] and accepted[7] == "3.0"
    assert accepted[-1] == "d@test.uz"
    declined = by_name["'=HYPERLINK(\"x\")"]
    assert declined[-1] == ""                            # rad etgan — email yo'q


async def test_candidates_csv_has_no_hidden_or_email(client, world):
    res = await client.get("/api/v1/talents/report/candidates.csv", headers=world["alpha_h"])
    header, *rows = _rows(res)
    assert header[:4] == ["full_name", "overall_score", "runs_completed", "sectors"]
    assert "technical" in header and not any("email" in h for h in header)
    assert [r[0] for r in rows] == ["Dilnoza Karimova", "'=HYPERLINK(\"x\")"]   # ball bo'yicha
    assert rows[0][1:4] == ["82.0", "2", "Banking, IT"]
    assert not any("@" in cell for row in rows for cell in row)


# ── Sof funksiyalar ──────────────────────────────────────────────────


def _profile(score, last):
    p = Profile(user_id=None)
    p.runs.append(RunSummary(
        run_id=None, scenario_id=None, scenario_title="t", company_name="c", sector="IT",
        completed_at=last, overall_score=score, competency_scores={}, strengths=[],
    ))
    return p


def test_score_bands_edges():
    at = datetime(2026, 9, 1, tzinfo=timezone.utc)
    stats = report.pool_stats([_profile(s, at) for s in (0, 49.9, 50, 69.9, 70, 84.9, 85, 100, None)], None)
    assert [b["candidates"] for b in stats["score_bands"]] == [2, 2, 2, 2]
    assert stats["candidates"] == 9


def test_by_month_uses_tashkent_time_and_fills_gaps():
    utc = timezone.utc
    offers = [
        TalentOffer(position_title="x", status=TalentOfferStatus.SENT, created_at=datetime(2026, 7, 10, tzinfo=utc)),
        # 31-avgust 20:00 UTC = 1-sentyabr 01:00 Toshkent
        TalentOffer(position_title="x", status=TalentOfferStatus.RESPONDED, response=OfferResponse.ACCEPTED,
                    created_at=datetime(2026, 8, 31, 20, tzinfo=utc)),
    ]
    rows = report.by_month(offers, None, datetime(2026, 10, 7, tzinfo=utc))
    assert [(r["month"], r["sent"], r["accepted"]) for r in rows] == [
        ("2026-07", 1, 0), ("2026-08", 0, 0), ("2026-09", 1, 1), ("2026-10", 0, 0),
    ]
    year_end = report.by_month(offers[:1], datetime(2025, 11, 20, tzinfo=utc), datetime(2026, 2, 1, tzinfo=utc))
    assert [r["month"] for r in year_end][:3] == ["2025-11", "2025-12", "2026-01"]


def test_csv_cell_escaping():
    assert report._cell("=1+1") == "'=1+1"
    assert report._cell("@SUM") == "'@SUM"
    assert report._cell("\tx") == "'\tx"
    assert report._cell("Odatiy") == "Odatiy"
    assert report._cell(None) == ""
    assert report._cell(datetime(2026, 10, 7, 4, 30, tzinfo=timezone.utc)) == "2026-10-07 09:30"
