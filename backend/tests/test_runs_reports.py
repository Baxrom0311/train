"""Kunlik va yakuniy hisobotlar, kompetensiya ballari (CONTRACT.md §9.6)."""
from datetime import timedelta

from sqlalchemy import select

from app.ai.reports import DaySummary, FinalSummary
from app.models.enums import AIEvalStatus, RunStatus
from app.models.simulation import Submission
from app.scenario.engine import Answer, submit_answer
from app.scenario.reports import (
    competency_scores,
    pending_day_reports,
    pending_final_reports,
    write_day_report,
    write_final_report,
)
from tests.test_runs_api import _login, clock, queue, scenario  # noqa: F401,F811
from tests.test_runs_engine import T, _events, _step, setup  # noqa: F401,F811


async def _grade(db, run, node_id, score):
    events = await _events(db, run)
    subs = (await db.execute(
        select(Submission).where(Submission.run_event_id == events[node_id].id)
    )).scalars().all()
    for s in subs:
        s.ai_score = score
        s.ai_eval_status = AIEvalStatus.COMPLETED
    await db.commit()


async def _completed_run(db, setup):
    run, _ = await setup(T("09:00"))
    await _step(db, run, T("09:00"))
    await submit_answer(db, run, "standup", Answer(text="Reja"), T("09:10"))
    await db.commit()
    await _grade(db, run, "standup", 80)
    await _step(db, run, T("09:30"))
    await submit_answer(db, run, "bug_orders", Answer(text="fix"), T("10:00"))
    await db.commit()
    await _grade(db, run, "bug_orders", 90)
    await _step(db, run, T("17:30"))
    await submit_answer(db, run, "day1_end", Answer(text="Bugun bug tuzatdim"), T("17:40"))
    await db.commit()
    await _grade(db, run, "day1_end", 70)
    await db.refresh(run)
    assert run.status == RunStatus.COMPLETED
    return run


def _summarizers(initiative=60.0, fail=False):
    calls = {}

    async def day(day_no, tasks, text):
        calls["day"] = (day_no, tasks, text)
        return None if fail else DaySummary(strengths=["Tez"], improvements=["Test"], advice="Ertaga test yozing")

    async def final(tasks, competencies, messages, completed):
        calls["final"] = (tasks, competencies, messages, completed)
        return None if fail else FinalSummary(summary="Yaxshi kun", strengths=["a"], improvements=["b"],
                                              initiative_score=initiative)

    return day, final, calls


async def test_day_and_final_report(db_session, setup):
    run = await _completed_run(db_session, setup)
    assert await pending_day_reports(db_session) == [(run.id, "day1_end")]
    assert await pending_final_reports(db_session) == [run.id]

    day, final, calls = _summarizers()
    assert await write_day_report(db_session, run.id, "day1_end", T("17:41"), summarize=day)
    events = await _events(db_session, run)
    report = events["day1_end"].result["report"]
    assert [t["node_id"] for t in report["tasks"]] == ["standup", "bug_orders", "day1_end"]   # incident skipped
    assert report["average_score"] == 80.0 and report["on_time_rate"] == 100.0
    assert report["summary"]["advice"] == "Ertaga test yozing"
    assert calls["day"][2] == "Bugun bug tuzatdim"
    assert await pending_day_reports(db_session) == []

    assert await write_final_report(db_session, run.id, T("17:41"), summarize=final)
    await db_session.refresh(run)
    assert run.competency_scores == {
        "technical": 90.0,
        "communication": 75.0,          # standup 80 + day_end 70
        "time_management": 100.0,       # teglangan task yo'q — o'z vaqtida ulushi
        "initiative": 60.0,             # AI transkript bahosi
    }
    assert run.final_report["overall_score"] == 80.0
    assert run.final_report["certificate"] and not run.final_report["incomplete"]
    assert calls["final"][3] is True
    assert await pending_final_reports(db_session) == []
    # qayta chaqiruv — o'zgarmaydi
    assert await write_final_report(db_session, run.id, T("18:00"), summarize=final)


async def test_reports_wait_for_pending_evaluation(db_session, setup):
    run = await _completed_run(db_session, setup)
    sub = (await db_session.execute(
        select(Submission).where(Submission.run_id == run.id).order_by(Submission.submitted_at.desc())
    )).scalars().first()
    sub.ai_eval_status = AIEvalStatus.PENDING
    sub.ai_score = None
    await db_session.commit()

    day, final, _ = _summarizers()
    assert not await write_final_report(db_session, run.id, T("17:50"), summarize=final)
    assert not await write_day_report(db_session, run.id, "day1_end", T("17:50"), summarize=day)
    # 15 daqiqadan keyin baholanmagan javobsiz yoziladi
    assert await write_final_report(db_session, run.id, T("17:40") + timedelta(minutes=15), summarize=final)
    await db_session.refresh(run)
    assert "communication" in run.competency_scores
    assert [t["score"] for t in run.final_report["tasks"] if t["node_id"] == "day1_end"] == [None]


async def test_expired_run_report_is_incomplete(db_session, setup):
    run, _ = await setup(T("09:00"))
    await _step(db_session, run, T("09:30"))
    await _step(db_session, run, T("18:00", day=9))
    assert run.status == RunStatus.EXPIRED

    day, final, calls = _summarizers(fail=True)      # AI ishlamaydi
    assert await write_final_report(db_session, run.id, T("18:01", day=9), summarize=final)
    await db_session.refresh(run)
    report = run.final_report
    assert report["incomplete"] and not report["certificate"] and report["summary"] is None
    assert report["overall_score"] == 0.0 and report["on_time_rate"] == 0.0
    assert "initiative" not in run.competency_scores
    assert calls["final"][3] is False
    # day_end expire paytida missed → kunlik hisobot ham kerak
    assert await pending_day_reports(db_session) == [(run.id, "day1_end")]
    assert await write_day_report(db_session, run.id, "day1_end", T("18:01", day=9), summarize=day)


def test_competency_scores_without_data():
    assert competency_scores([]) == {}


async def test_cron_enqueues_report_jobs(db_session, setup):
    from app.scenario.jobs import DAY_REPORT_JOB, FINAL_REPORT_JOB, deliver_due_events
    from tests.conftest import TestingSessionLocal

    run = await _completed_run(db_session, setup)

    class Queue:
        def __init__(self):
            self.jobs = []

        async def enqueue_job(self, name, *args, **kwargs):
            self.jobs.append((name, args, kwargs["_job_id"]))

    q = Queue()
    await deliver_due_events({"session_factory": TestingSessionLocal, "redis": q})
    assert (DAY_REPORT_JOB, (str(run.id), "day1_end"), f"day-report:{run.id}:day1_end") in q.jobs
    assert (FINAL_REPORT_JOB, (str(run.id),), f"final-report:{run.id}") in q.jobs


async def test_report_endpoint(client, test_user_factory, scenario, clock, queue):
    h = await _login(client, test_user_factory, "rep@example.com")
    other = await _login(client, test_user_factory, "rep-other@example.com")
    run_id = (await client.post("/api/v1/runs", json={"scenario_id": str(scenario)}, headers=h)).json()["run"]["id"]
    r = await client.get(f"/api/v1/runs/{run_id}/report", headers=h)
    assert r.status_code == 200
    assert r.json() == {
        "run_id": run_id, "status": "active", "days": [], "final": None,
        "competency_scores": None, "final_pending": False,
    }
    assert (await client.get(f"/api/v1/runs/{run_id}/report", headers=other)).status_code == 404
    await client.post(f"/api/v1/runs/{run_id}/abandon", headers=h)
    assert (await client.get(f"/api/v1/runs/{run_id}/report", headers=h)).json()["final_pending"] is False
