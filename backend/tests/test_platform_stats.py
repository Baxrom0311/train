"""
Platforma statistikasi va AI sarfi (CONTRACT.md §21).

AI hisobi: `chat()` har urinishni `ai_usage`ga yig'adi (muvaffaqiyat — calls va
tokenlar, xato — failures). Statistika: davr Toshkent kunlari bo'yicha, Run'lar
boshlangan vaqti bo'yicha, baholash navbati — hozirgi holat.
"""
import json
from datetime import UTC, date, datetime, timedelta

import httpx
import pytest
from sqlalchemy import select

from app.ai import usage
from app.ai.llm import chat
from app.analytics import platform
from app.config import settings
from app.models.ai_usage import AIUsage
from app.models.billing import Company
from app.models.enums import AIEvalStatus, RunStatus, Sector
from app.models.scenario import RunEvent
from app.models.simulation import Submission
from tests.test_ai_layer import Echo, _client, _gemini_reply, keys  # noqa: F401
from tests.test_talent_hunt import NOW, _headers, _run, _scenario

# 7-oktabr 03:00 Toshkent — UTC bo'yicha hali 6-oktabr
LATE_EVENING_UTC = datetime(2026, 10, 6, 22, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _no_expire(db_session):
    db_session.sync_session.expire_on_commit = False


@pytest.fixture
async def admin(client, test_user_factory):
    await test_user_factory("admin@tryjob.test", "pass", "admin")
    return await _headers(client, "admin@tryjob.test")


async def _usage(db, day, provider, purpose, *, calls=1, failures=0, tokens_in=0, tokens_out=0, model="m"):
    db.add(AIUsage(day=day, provider=provider, model=model, purpose=purpose, calls=calls,
                   failures=failures, tokens_in=tokens_in, tokens_out=tokens_out))
    await db.commit()


# ── AI sarfini yozish ────────────────────────────────────────────────


async def test_chat_records_success_and_failures(keys, db_session):  # noqa: F811
    def handler(request):
        if request.url.host == "api.deepseek.com":
            return httpx.Response(500)
        return httpx.Response(200, json=_gemini_reply('{"answer": "ok"}'))

    async with _client(handler) as client:
        for _ in range(2):
            assert await chat([{"role": "user", "content": "x"}], schema=Echo, client=client, purpose="mentor")

    rows = {r.provider: r for r in (await db_session.execute(select(AIUsage))).scalars()}
    assert set(rows) == {"deepseek", "gemini"}
    assert (rows["deepseek"].calls, rows["deepseek"].failures, rows["deepseek"].tokens_in) == (0, 2, 0)
    gemini = rows["gemini"]
    assert (gemini.calls, gemini.failures, gemini.purpose, gemini.model) == (2, 0, "mentor", settings.GEMINI_MODEL)
    assert gemini.tokens_in + gemini.tokens_out == 36           # 2 × 18 (fake javob)
    assert gemini.day == usage.today()


async def test_unknown_purpose_is_other_and_record_never_raises(db_session, monkeypatch):
    await usage.record("deepseek", "m", "nimadir", tokens_in=3)
    row = (await db_session.execute(select(AIUsage))).scalars().one()
    assert row.purpose == "other" and row.tokens_in == 3

    class Broken:
        def __call__(self):
            raise RuntimeError("db yo'q")

    monkeypatch.setattr("app.database.AsyncSessionLocal", Broken())
    await usage.record("deepseek", "m", "mentor")               # xato yutiladi, log bo'ladi


def test_llm_prices_parsing(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PRICES", " DeepSeek=0.27/1.10, gemini=0.1/0.4,buzuq,openai=x/1")
    assert settings.llm_prices == {"deepseek": (0.27, 1.10), "gemini": (0.1, 0.4)}
    assert usage.cost_usd("deepseek", 1_000_000, 500_000) == pytest.approx(0.82)
    assert usage.cost_usd("openai", 10, 10) is None


# ── Statistika ───────────────────────────────────────────────────────


async def test_requires_permission(client, test_user_factory, admin):
    await test_user_factory("s@test.uz", "pass", "student")
    student = await _headers(client, "s@test.uz")
    assert (await client.get("/api/v1/admin/platform", headers=student)).status_code == 403
    assert (await client.get("/api/v1/admin/platform")).status_code == 401
    assert (await client.get("/api/v1/admin/platform?days=14", headers=admin)).status_code == 422
    assert (await client.get("/api/v1/admin/platform?days=7", headers=admin)).status_code == 200


async def test_platform_overview(client, db_session, test_user_factory, admin, monkeypatch):
    monkeypatch.setattr(settings, "LLM_PRICES", "deepseek=1/2")
    s = test_user_factory
    old = await s("old@test.uz", "pass", "student")
    old.created_at = NOW - timedelta(days=60)
    new = await s("new@test.uz", "pass", "student")
    await s("off@test.uz", "pass", "student", is_active=False)
    db_session.add_all([
        Company(name="A", industry="IT", contact_email="a@a.test", is_verified=True),
        Company(name="B", industry="IT", contact_email="b@b.test", is_verified=False),
    ])
    await db_session.commit()

    it = await _scenario(db_session, "it-day1")
    bank = await _scenario(db_session, "bank-day1", Sector.BANKING)
    r1 = await _run(db_session, new, it, score=80.0, competencies={})
    r2 = await _run(db_session, old, it, score=60.0, competencies={})
    await _run(db_session, new, bank, score=0, competencies={}, status=RunStatus.EXPIRED)
    await _run(db_session, old, bank, score=0, competencies={}, status=RunStatus.ACTIVE)
    ancient = await _run(db_session, old, it, score=99.0, competencies={}, days_ago=50)
    ancient.created_at = NOW - timedelta(days=50)

    e1, e2 = RunEvent(run_id=r1.id, node_id="t1", scheduled_at=NOW), RunEvent(run_id=r2.id, node_id="t1", scheduled_at=NOW)
    db_session.add_all([e1, e2])
    await db_session.flush()

    def answer(run, event, attempt, status, ago=timedelta()):
        return Submission(user_id=run.user_id, run_id=run.id, run_event_id=event.id, attempt=attempt,
                          content="javob", ai_eval_status=status, submitted_at=NOW - ago)

    db_session.add_all([
        answer(r1, e1, 1, AIEvalStatus.PENDING, timedelta(minutes=45)),
        answer(r1, e1, 2, AIEvalStatus.QUEUED_RETRY, timedelta(minutes=5)),
        answer(r2, e2, 1, AIEvalStatus.FAILED_PERMANENT, timedelta(days=1)),
        answer(r2, e2, 2, AIEvalStatus.COMPLETED),
    ])
    await db_session.commit()

    today = usage.today()
    await _usage(db_session, today, "deepseek", "evaluation", calls=3, tokens_in=600_000, tokens_out=200_000)
    await _usage(db_session, today, "gemini", "persona", calls=2, failures=1, tokens_in=100, tokens_out=50, model="g")
    await _usage(db_session, today - timedelta(days=2), "deepseek", "persona", tokens_in=100_000)
    await _usage(db_session, today - timedelta(days=40), "deepseek", "evaluation", tokens_in=9_000_000)

    body = (await client.get("/api/v1/admin/platform?days=30", headers=admin)).json()
    assert body["days"] == 30
    assert body["users"] == {
        "students": 2, "companies": 1, "universities": 0, "new_students": 1, "active_students": 2,
    }
    assert body["runs"] == {
        "in_progress": 1, "started": 4, "completed": 2, "expired": 1, "abandoned": 0,
        "completion_rate": 66.7, "avg_score": 70.0,                 # 50 kun oldingi Run kirmaydi
    }
    ev = body["evaluation"]
    assert (ev["pending"], ev["queued_retry"], ev["failed"]) == (1, 1, 1)
    assert 44 <= ev["oldest_pending_minutes"] <= 46

    ai = body["ai"]
    assert (ai["calls"], ai["failures"], ai["tokens_in"], ai["tokens_out"]) == (6, 1, 700_100, 200_050)
    assert ai["cost_usd"] == pytest.approx(0.6 + 0.4 + 0.1)          # gemini narxsiz
    assert ai["cost_complete"] is False
    assert [p["purpose"] for p in ai["by_purpose"]] == ["evaluation", "persona"]
    assert ai["by_purpose"][1] == {"purpose": "persona", "calls": 3, "tokens": 100_150, "cost_usd": 0.1}
    assert [(p["provider"], p["cost_usd"]) for p in ai["by_provider"]] == [("deepseek", 1.1), ("gemini", None)]

    daily = body["daily"]
    assert len(daily) == 30 and daily[-1]["day"] == today.isoformat()
    assert daily[-1]["ai_tokens"] == 800_150 and daily[-1]["ai_cost_usd"] == 1.0
    assert daily[-3]["ai_tokens"] == 100_000
    assert sum(d["runs_started"] for d in daily) == 4
    assert sum(d["runs_completed"] for d in daily) == 2
    assert sum(d["new_students"] for d in daily) == 1

    assert body["scenarios"] == [                                    # teng — nom bo'yicha
        {"scenario_id": str(bank.scenario_id), "title": "bank-day1 title", "sector": "Banking",
         "started": 2, "completed": 0, "completion_rate": 0.0, "avg_score": None},
        {"scenario_id": str(it.scenario_id), "title": "it-day1 title", "sector": "IT",
         "started": 2, "completed": 2, "completion_rate": 100.0, "avg_score": 70.0},
    ]


async def test_empty_platform(client, admin):
    body = (await client.get("/api/v1/admin/platform?days=7", headers=admin)).json()
    assert body["runs"]["completion_rate"] is None and body["runs"]["avg_score"] is None
    assert body["evaluation"]["oldest_pending_minutes"] is None
    assert body["ai"]["cost_usd"] is None and body["ai"]["cost_complete"] is True
    assert len(body["daily"]) == 7 and body["scenarios"] == []


def test_period_uses_tashkent_days():
    first, since = platform.period(LATE_EVENING_UTC, 7)
    assert first == date(2026, 10, 1)                                # bugun Toshkentda 7-oktabr
    assert since == datetime(2026, 9, 30, 19, 0, tzinfo=UTC)        # 1-oktabr 00:00 Toshkent
