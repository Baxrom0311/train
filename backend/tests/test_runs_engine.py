"""Run dvigateli: yetkazish, dedlaynlar, shartlar, yakunlash (CONTRACT.md §9.2, §9.8)."""
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml
from sqlalchemy import select

from app.ai.evaluator import CriterionScore, RubricResult
from app.ai.llm import LLMResult
from app.models.enums import AIEvalStatus, HolidaySource, RunEventStatus, RunStatus
from app.models.scenario import RunEvent, WorkHoliday
from app.models.simulation import Submission
from app.scenario.clock import TASHKENT
from app.scenario.engine import (
    Answer,
    Conflict,
    Invalid,
    NotFound,
    abandon,
    advance,
    create_run,
    decide,
    submit_answer,
)
from app.scenario.evaluation import evaluate_run_submission, penalty_factor
from app.scenario.holidays import sync_work_holidays
from app.scenario.importer import import_scenario, publish_version
from app.scenario.schema import ScenarioDefinition

FIXTURE = Path(__file__).parent / "fixtures" / "scenarios" / "elon-market-backend-day1.yaml"

DECISION_NODES = [
    {
        "id": "release_call", "type": "decision", "day": 1, "at": "11:00", "from": "dilnoza",
        "brief": "Reliz bugun chiqsinmi?",
        "options": [
            {"key": "ship", "label": "Chiqaramiz", "grade": "wrong", "flag": "rushed"},
            {"key": "wait", "label": "Testlardan keyin", "grade": "correct"},
        ],
    },
    {
        "id": "rollback_note", "type": "message", "day": 1, "at": "11:30", "from": "dilnoza",
        "when": {"flag": "rushed"}, "brief": "Reliz qaytarib olindi.",
    },
]


def T(hhmm: str, day: int = 7) -> datetime:
    """2026-10-07 (chorshanba) Toshkent vaqti."""
    h, m = map(int, hhmm.split(":"))
    return datetime(2026, 10, day, h, m, tzinfo=TASHKENT)


def _defn(extra_nodes=()) -> ScenarioDefinition:
    data = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    data["nodes"] = [*data["nodes"][:-1], *extra_nodes, data["nodes"][-1]]
    return ScenarioDefinition.model_validate(data)


@pytest.fixture
async def setup(db_session, test_user_factory):
    async def _setup(start: datetime, extra_nodes=(), now: datetime | None = None):
        user = await test_user_factory(f"eng{start.timestamp():.0f}@example.com", "pass")
        version, _ = await import_scenario(db_session, _defn(extra_nodes))
        await publish_version(db_session, version)
        run, info = await create_run(db_session, user.id, version, now or start, start)
        await db_session.commit()
        return run, info
    return _setup


async def _events(db, run) -> dict[str, RunEvent]:
    rows = (await db.execute(select(RunEvent).where(RunEvent.run_id == run.id))).scalars().all()
    for r in rows:
        await db.refresh(r)
    return {e.node_id: e for e in rows}


async def _step(db, run, now):
    notes = await advance(db, now.astimezone(timezone.utc))
    await db.commit()
    await db.refresh(run)
    return notes


async def test_create_schedules_fixed_nodes(db_session, setup):
    run, info = await setup(T("09:00"))
    assert run.status == RunStatus.ACTIVE and info.warning is None
    events = await _events(db_session, run)
    assert set(events) == {"welcome", "standup", "bug_orders", "incident_payments", "day1_end"}
    assert events["incident_payments"].scheduled_at == T("14:00")
    assert run.ends_at == T("18:00", day=9)            # chorshanba + 2 ish kuni
    assert info.day1_ends_at == T("18:00")


async def test_late_start_shifts_schedule_and_warns(db_session, setup):
    run, info = await setup(T("15:00"))
    assert info.warning and info.day1_ends_at == T("15:00", day=8)
    events = await _events(db_session, run)
    assert events["bug_orders"].scheduled_at == T("15:30")
    # 14:00 + 5 ish soati → ertasi 10:00
    assert events["incident_payments"].scheduled_at == T("10:00", day=8)


async def test_future_start_is_scheduled_then_activates(db_session, setup):
    run, _ = await setup(T("09:00", day=8), now=T("20:00"))
    assert run.status == RunStatus.SCHEDULED
    await _step(db_session, run, T("08:59", day=8))
    assert run.status == RunStatus.SCHEDULED
    await _step(db_session, run, T("09:00", day=8))
    events = await _events(db_session, run)
    assert run.status == RunStatus.ACTIVE
    assert events["welcome"].status == RunEventStatus.DELIVERED


async def test_past_start_rejected(db_session, setup):
    with pytest.raises(Invalid):
        await setup(T("09:00"), now=T("10:00"))


async def test_delivery_due_and_missed(db_session, setup):
    run, _ = await setup(T("09:00"))
    await _step(db_session, run, T("09:00"))
    events = await _events(db_session, run)
    assert events["welcome"].status == RunEventStatus.DELIVERED and events["welcome"].due_at is None
    assert events["standup"].due_at == T("09:20")
    assert events["bug_orders"].status == RunEventStatus.PENDING

    await _step(db_session, run, T("09:30"))
    events = await _events(db_session, run)
    assert events["standup"].status == RunEventStatus.MISSED
    assert events["standup"].result["missed_at"]
    assert events["bug_orders"].due_at == T("11:30")


async def test_due_counts_from_delivery_not_schedule(db_session, setup):
    """§9.2: cron kechiksa talaba vaqt yo'qotmaydi."""
    run, _ = await setup(T("09:00"))
    await _step(db_session, run, T("10:00"))
    events = await _events(db_session, run)
    assert events["bug_orders"].delivered_at == T("10:00")
    assert events["bug_orders"].due_at == T("12:00")


async def test_submit_spawns_after_node_and_late_flag(db_session, setup):
    run, _ = await setup(T("09:00"))
    await _step(db_session, run, T("09:00"))
    await _step(db_session, run, T("09:30"))
    sub, _ = await submit_answer(db_session, run, "bug_orders", Answer(text="None tekshiruvi"), T("10:00"))
    await db_session.commit()
    assert sub.attempt == 1 and not sub.late and sub.ai_eval_status == AIEvalStatus.PENDING
    events = await _events(db_session, run)
    assert events["lead_followup"].scheduled_at == T("10:15")

    # Kech topshirish: missed → submitted, missed belgisi saqlanadi
    late, _ = await submit_answer(db_session, run, "standup", Answer(text="Reja"), T("10:05"))
    await db_session.commit()
    events = await _events(db_session, run)
    assert late.late and events["standup"].status == RunEventStatus.SUBMITTED
    assert events["standup"].result["missed_at"]

    await _step(db_session, run, T("10:15"))
    assert (await _events(db_session, run))["lead_followup"].status == RunEventStatus.DELIVERED


async def test_submit_validation(db_session, setup):
    run, _ = await setup(T("09:00"))
    await _step(db_session, run, T("09:30"))
    with pytest.raises(NotFound):          # hali yetkazilmagan
        await submit_answer(db_session, run, "day1_end", Answer(text="x"), T("09:31"))
    with pytest.raises(Invalid):           # standup faqat text
        await submit_answer(db_session, run, "standup", Answer(link_url="https://x.example"), T("09:31"))
    with pytest.raises(Invalid):           # message'ga javob yo'q
        await submit_answer(db_session, run, "welcome", Answer(text="x"), T("09:31"))
    with pytest.raises(Invalid):
        await submit_answer(db_session, run, "bug_orders", Answer(), T("09:31"))


async def test_max_attempts(db_session, setup):
    run, _ = await setup(T("09:00"))
    await _step(db_session, run, T("09:30"))
    for i in range(3):
        sub, _ = await submit_answer(db_session, run, "bug_orders", Answer(code=f"v{i}"), T("10:00"))
        assert sub.attempt == i + 1
    with pytest.raises(Conflict):
        await submit_answer(db_session, run, "bug_orders", Answer(code="v4"), T("10:00"))
    await db_session.commit()


async def _scored_submission(db, run, score, status=AIEvalStatus.COMPLETED):
    sub, _ = await submit_answer(db, run, "bug_orders", Answer(text="fix"), T("10:00"))
    sub.ai_eval_status = status
    sub.ai_score = score
    await db.commit()


@pytest.mark.parametrize("score,expected", [(40, RunEventStatus.DELIVERED), (80, RunEventStatus.SKIPPED)])
async def test_when_score_branch(db_session, setup, score, expected):
    run, _ = await setup(T("09:00"))
    await _step(db_session, run, T("09:30"))
    await _scored_submission(db_session, run, score)
    await _step(db_session, run, T("14:00"))
    assert (await _events(db_session, run))["incident_payments"].status == expected


async def test_when_missed_branch(db_session, setup):
    run, _ = await setup(T("09:00"))
    await _step(db_session, run, T("09:30"))
    await _step(db_session, run, T("14:00"))
    events = await _events(db_session, run)
    assert events["bug_orders"].status == RunEventStatus.MISSED
    assert events["incident_payments"].status == RunEventStatus.DELIVERED


async def test_score_wait_up_to_15_minutes(db_session, setup):
    run, _ = await setup(T("09:00"))
    await _step(db_session, run, T("09:30"))
    await _scored_submission(db_session, run, None, status=AIEvalStatus.PENDING)
    await _step(db_session, run, T("14:10"))
    assert (await _events(db_session, run))["incident_payments"].status == RunEventStatus.PENDING
    await _step(db_session, run, T("14:15"))
    # baho kelmadi → score_lt false, missed false → skipped
    assert (await _events(db_session, run))["incident_payments"].status == RunEventStatus.SKIPPED


async def test_chronological_order_when_cron_lags(db_session, setup):
    """Cron 09:00–15:00 ishlamagan: 09:30 dagi task 15:00 da yetkaziladi, 14:00 dagi shart missed ko'rmaydi."""
    run, _ = await setup(T("09:00"))
    await _step(db_session, run, T("15:00"))
    events = await _events(db_session, run)
    assert events["standup"].status == RunEventStatus.DELIVERED   # 15:00 da yetkazildi, dedlayn 15:20
    assert events["bug_orders"].status == RunEventStatus.DELIVERED
    assert events["incident_payments"].status == RunEventStatus.SKIPPED


async def test_completion(db_session, setup):
    run, _ = await setup(T("09:00"))
    await _step(db_session, run, T("09:00"))
    await submit_answer(db_session, run, "standup", Answer(text="Reja"), T("09:10"))
    await _step(db_session, run, T("09:30"))
    await _scored_submission(db_session, run, 90)
    await _step(db_session, run, T("17:30"))
    assert run.status == RunStatus.ACTIVE
    _, notes = await submit_answer(db_session, run, "day1_end", Answer(text="Bugun bug tuzatdim"), T("17:40"))
    await db_session.commit()
    await db_session.refresh(run)
    assert run.status == RunStatus.COMPLETED
    assert notes[-1].data == {"status": "completed"}


async def test_completion_waits_for_open_deadline(db_session, setup):
    """Kun yakuni topshirildi, lekin task dedlayni hali o'tmagan — Run ochiq qoladi."""
    run, _ = await setup(T("17:00"))     # bug_orders 17:30 da, dedlayn ertasi
    await _step(db_session, run, T("09:30", day=8))
    await _step(db_session, run, T("16:30", day=8))
    events = await _events(db_session, run)
    assert events["day1_end"].status == RunEventStatus.DELIVERED
    await submit_answer(db_session, run, "day1_end", Answer(text="Hisobot"), T("16:35", day=8))
    await db_session.commit()
    await db_session.refresh(run)
    events = await _events(db_session, run)
    open_graded = [n for n, e in events.items() if e.status == RunEventStatus.DELIVERED and n != "welcome"]
    assert open_graded and run.status == RunStatus.ACTIVE


async def test_expire_by_ends_at(db_session, setup):
    run, _ = await setup(T("09:00"))
    await _step(db_session, run, T("09:00"))
    await _step(db_session, run, T("18:00", day=9))
    events = await _events(db_session, run)
    assert run.status == RunStatus.EXPIRED
    assert events["day1_end"].status == RunEventStatus.MISSED
    assert events["welcome"].status == RunEventStatus.DELIVERED


async def test_expire_by_inactivity(db_session, setup):
    run, _ = await setup(T("09:00"))
    run.ends_at = T("09:00") + timedelta(days=30)
    await db_session.commit()
    await _step(db_session, run, T("09:00") + timedelta(days=7))
    events = await _events(db_session, run)
    assert run.status == RunStatus.EXPIRED
    assert events["day1_end"].status == RunEventStatus.MISSED     # yetkazilgan, keyin yopilgan


async def test_abandon(db_session, setup):
    run, _ = await setup(T("09:00"))
    await _step(db_session, run, T("09:00"))
    await abandon(db_session, run, T("09:05"))
    await db_session.commit()
    events = await _events(db_session, run)
    assert run.status == RunStatus.ABANDONED
    assert events["standup"].status == RunEventStatus.MISSED
    assert events["bug_orders"].status == RunEventStatus.SKIPPED
    with pytest.raises(Conflict):
        await abandon(db_session, run, T("09:06"))
    with pytest.raises(Conflict):
        await submit_answer(db_session, run, "standup", Answer(text="x"), T("09:06"))


async def test_decision_sets_flag_and_branches(db_session, setup):
    run, _ = await setup(T("09:00"), extra_nodes=DECISION_NODES)
    await _step(db_session, run, T("11:00"))
    with pytest.raises(Invalid):
        await decide(db_session, run, "release_call", "maybe", T("11:05"))
    sub, _ = await decide(db_session, run, "release_call", "ship", T("11:05"))
    await db_session.commit()
    assert sub.ai_score == 0 and sub.ai_eval_status == AIEvalStatus.COMPLETED
    assert run.flags == ["rushed"]
    with pytest.raises(Conflict):
        await decide(db_session, run, "release_call", "wait", T("11:06"))
    await _step(db_session, run, T("11:30"))
    events = await _events(db_session, run)
    assert events["release_call"].choice == "ship"
    assert events["rollback_note"].status == RunEventStatus.DELIVERED


async def test_late_decision_penalty(db_session, setup):
    run, _ = await setup(T("09:00"), extra_nodes=DECISION_NODES)
    await _step(db_session, run, T("11:00"))
    await _step(db_session, run, T("12:30"))           # 11:00 + 60 → 12:00 dedlayn o'tdi
    assert (await _events(db_session, run))["release_call"].status == RunEventStatus.MISSED
    sub, _ = await decide(db_session, run, "release_call", "wait", T("12:31"))
    await db_session.commit()
    assert sub.late and sub.ai_score == 80.0


async def test_holiday_shifts_schedule(db_session, setup):
    db_session.add(WorkHoliday(date=date(2026, 10, 8), name="Test bayram", source=HolidaySource.MANUAL))
    await db_session.commit()
    run, info = await setup(T("15:00"))
    assert info.day1_ends_at == T("15:00", day=9)          # payshanba o'tkazib yuborildi
    assert run.ends_at == T("18:00", day=13)               # juma + dushanba, seshanba


async def test_evaluation_applies_penalties(db_session, setup):
    run, _ = await setup(T("09:00"))
    await _step(db_session, run, T("09:30"))
    sub, _ = await submit_answer(db_session, run, "bug_orders", Answer(text="Refund amount None"), T("12:00"))
    await db_session.commit()
    assert sub.late

    calls = []

    async def fake_evaluate(brief, answer, rubric, *, reference_answer, sector):
        calls.append((brief, answer, [c.id for c in rubric], reference_answer, sector))
        return RubricResult(
            criteria=[CriterionScore(id="root_cause", score=90), CriterionScore(id="fix_quality", score=90)],
            score=90.0, short_feedback="Yaxshi",
            llm=LLMResult(text="{}", data=None, provider="fake", model="fake"),
        )

    notes, retry = await evaluate_run_submission(db_session, sub.id, T("12:01"), evaluate=fake_evaluate)
    stored = await db_session.get(Submission, sub.id)
    await db_session.refresh(stored)
    assert not retry and stored.ai_eval_status == AIEvalStatus.COMPLETED
    assert stored.ai_score == 72.0                            # 90 × (1 − 0.2)
    assert stored.rubric_scores["raw_score"] == 90.0 and stored.rubric_scores["penalty_factor"] == 0.8
    assert [c["id"] for c in stored.rubric_scores["criteria"]] == ["root_cause", "fix_quality"]
    brief, answer, ids, reference, sector = calls[0]
    assert ids == ["root_cause", "fix_quality"] and reference and sector == "IT"
    assert notes[0].data["score"] == 72.0


async def test_evaluation_retry_then_permanent(db_session, setup):
    run, _ = await setup(T("09:00"))
    await _step(db_session, run, T("09:30"))
    sub, _ = await submit_answer(db_session, run, "bug_orders", Answer(text="fix"), T("10:00"))
    await db_session.commit()

    async def down(*args, **kwargs):
        return None

    _, retry = await evaluate_run_submission(db_session, sub.id, T("10:01"), job_try=1, evaluate=down)
    assert retry
    _, retry = await evaluate_run_submission(db_session, sub.id, T("10:05"), job_try=3, evaluate=down)
    stored = await db_session.get(Submission, sub.id)
    await db_session.refresh(stored)
    assert not retry and stored.ai_eval_status == AIEvalStatus.FAILED_PERMANENT


def test_penalty_factor():
    node = _defn().node("bug_orders")
    assert penalty_factor(node, late=False, hints_used=0) == 1
    assert penalty_factor(node, late=True, hints_used=2) == pytest.approx(0.8 * 0.8)


async def test_sync_work_holidays(db_session):
    db_session.add(WorkHoliday(date=date(2026, 1, 1), name="Admin yozuvi", source=HolidaySource.MANUAL))
    await db_session.commit()
    count = await sync_work_holidays(db_session, date(2026, 10, 7))
    await db_session.commit()
    assert count > 20
    manual = await db_session.get(WorkHoliday, date(2026, 1, 1))
    await db_session.refresh(manual)
    assert manual.name == "Admin yozuvi" and manual.source == HolidaySource.MANUAL

    # O'chirilgan auto sana keyingi sinxronizatsiyada qaytmaydi
    navruz = await db_session.get(WorkHoliday, date(2026, 3, 21))
    await db_session.delete(navruz)
    await db_session.commit()
    assert await sync_work_holidays(db_session, date(2026, 10, 7)) == 0
    await db_session.commit()
    assert await db_session.get(WorkHoliday, date(2026, 3, 21)) is None


async def test_cron_job_requeues_stale_pending(db_session, setup):
    from app.scenario.jobs import EVAL_JOB, deliver_due_events, eval_job_id
    from tests.conftest import TestingSessionLocal

    run, _ = await setup(T("09:00"))
    await _step(db_session, run, T("09:30"))
    sub, _ = await submit_answer(db_session, run, "bug_orders", Answer(text="fix"), T("10:00"))
    await db_session.commit()

    class Queue:
        jobs = []

        async def enqueue_job(self, name, *args, **kwargs):
            self.jobs.append((name, args, kwargs))

    q = Queue()
    await deliver_due_events({"session_factory": TestingSessionLocal, "redis": q})
    assert (EVAL_JOB, (str(sub.id),), {"_job_id": eval_job_id(sub.id)}) in q.jobs


def test_worker_settings_register_scenario_jobs():
    from app.ai.worker import WorkerSettings

    names = {getattr(f, "name", getattr(f, "__name__", None)) for f in WorkerSettings.functions}
    assert "evaluate_run_submission_job" in names
    assert {c.name for c in WorkerSettings.cron_jobs} == {
        "cron:deliver_due_events", "cron:sync_work_holidays_job", "cron:embed_document_chunks_job",
    }
