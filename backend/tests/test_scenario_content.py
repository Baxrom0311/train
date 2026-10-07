"""`backend/content/scenarios/` kontenti: sxema, sifat qoidalari va to'liq kun o'tishi (CONTRACT.md §9.11)."""
from pathlib import Path

import pytest
import yaml

from app.models.enums import AIEvalStatus, NodeType, RunEventStatus, RunStatus, Sector
from app.scenario.engine import Answer, create_run, decide, submit_answer
from app.scenario.importer import import_scenario, publish_version
from app.scenario.schema import ANSWER_TYPES, PersonaKind, ScenarioDefinition, scenario_warnings
from tests.test_runs_engine import T, _events, _step

CONTENT = Path(__file__).resolve().parents[1] / "content" / "scenarios"
FILES = sorted(CONTENT.glob("*.yaml"))


def _load(path: Path) -> ScenarioDefinition:
    return ScenarioDefinition.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def test_content_covers_every_sector():
    """§9.11: har sohada kamida bitta 1 kunlik ssenariy + IT haftaligi; har 1 kunlik `test_full_day`da."""
    defs = [_load(p) for p in FILES]
    assert sorted((d.sector.value, d.duration_days) for d in defs) == [
        ("Banking", 1), ("Data", 1), ("HR", 1), ("IT", 1), ("IT", 5), ("Marketing", 1)]
    assert {d.sector for d in defs} == set(Sector)
    assert {d.slug for d in defs if d.duration_days == 1} == set(PATHS)


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_content_quality(path):
    defn = _load(path)
    assert defn.slug == path.stem
    assert scenario_warnings(defn) == []
    assert any(p.kind == PersonaKind.MENTOR for p in defn.personas)

    used_docs = {d for n in defn.nodes for d in n.attachments} | {d for p in defn.personas for d in p.knows}
    assert used_docs == {d.key for d in defn.documents}, "har hujjat yo ilova, yo personaj biladi"
    speakers = {n.from_ for n in defn.nodes if n.from_}
    assert speakers == {p.key for p in defn.personas}, "har personaj kamida bitta skript xabar yozadi"

    for n in defn.nodes:
        if n.is_graded:
            assert n.competencies, n.id
        if n.type in ANSWER_TYPES:
            assert n.rubric and n.hints and n.reference_answer and n.attachments, n.id
        if n.type == NodeType.DECISION:
            assert {o.grade for o in n.options} >= {"correct", "wrong"}, n.id


async def _start(db, factory, path: Path, email: str):
    user = await factory(email, "pass")
    version, _ = await import_scenario(db, _load(path))
    await publish_version(db, version)
    run, _ = await create_run(db, user.id, version, T("09:00"), T("09:00"))
    await db.commit()
    return run


async def _answer(db, run, node_id, at, score):
    sub, _ = await submit_answer(db, run, node_id, Answer(text="javob"), at)
    sub.ai_eval_status = AIEvalStatus.COMPLETED
    sub.ai_score = score
    await db.commit()


# (fayl, asosiy task, qaror node'i, to'g'ri variant, xato variant, xato bayrog'i xabari, past ball xabari,
#  14:00 task, incident, incident vaqti)
PATHS = {
    "lazurit-go-backend-day1": (
        "bug_promo", "pm_request", "finish_bug", "switch_now", "lead_on_priority", "qa_retest_failed",
        "api_design", "incident_orders", "15:30",
    ),
    "oqsaroy-bank-credit-day1": (
        "credit_analysis", "client_pressure", "explain_process", "promise", "lead_on_promise", "mentor_review",
        "aml_review", "complaint_incident", "15:00",
    ),
    "oydinbarg-marketing-day1": (
        "campaign_analysis", "director_claim", "compliant_alternative", "publish_claim", "lead_on_claim", "mentor_review",
        "launch_copy", "price_incident", "15:00",
    ),
    "sabzazor-data-day1": (
        "weekly_report", "board_chart", "honest_note", "hide_store", "lead_on_hidden_data", "mentor_review",
        "ab_analysis", "dashboard_incident", "15:30",
    ),
    "qaldirgoch-qadoq-hr-day1": (
        "cv_screening", "manager_filter", "refuse_and_escalate", "follow_manager", "lead_on_filter", "mentor_review",
        "leave_calc", "leak_incident", "15:30",
    ),
}


@pytest.mark.parametrize("good", [True, False], ids=["strong", "weak"])
@pytest.mark.parametrize("slug", sorted(PATHS))
async def test_full_day(db_session, test_user_factory, slug, good):
    task, decision, right, wrong, flag_msg, low_msg, afternoon, incident, incident_at = PATHS[slug]
    run = await _start(db_session, test_user_factory, CONTENT / f"{slug}.yaml", f"{slug}-{good}@example.com")

    await _step(db_session, run, T("09:00"))
    await _answer(db_session, run, "standup", T("09:10"), 80)
    await _step(db_session, run, T("09:30"))
    if good:
        await _answer(db_session, run, task, T("10:30"), 90)
    await _step(db_session, run, T("11:30"))
    await decide(db_session, run, decision, right if good else wrong, T("11:35"))
    await db_session.commit()
    await _step(db_session, run, T("14:00"))
    await _answer(db_session, run, afternoon, T("14:30"), 70)
    await _step(db_session, run, T(incident_at))
    await _answer(db_session, run, incident, T(incident_at) + (T("09:20") - T("09:00")), 75)
    await _step(db_session, run, T("17:30"))

    events = await _events(db_session, run)
    branch = RunEventStatus.SKIPPED if good else RunEventStatus.DELIVERED
    assert events[flag_msg].status == branch
    assert events[low_msg].status == branch
    assert events[task].status == (RunEventStatus.SUBMITTED if good else RunEventStatus.MISSED)
    assert all(e.status != RunEventStatus.PENDING for e in events.values())
    assert run.flags == ([] if good else [next(
        o.flag for o in _load(CONTENT / f"{slug}.yaml").node(decision).options if o.key == wrong
    )])

    await _answer(db_session, run, "day1_end", T("17:40"), 80)
    await db_session.refresh(run)
    assert run.status == RunStatus.COMPLETED


WEEK = "lazurit-go-backend-week1"
WEEK_DAYS = {1: 7, 2: 8, 3: 9, 4: 12, 5: 13}   # chorshanba → keyingi seshanba (dam olish kunlari o'tkaziladi)


@pytest.mark.parametrize("good", [True, False], ids=["strong", "weak"])
async def test_full_week(db_session, test_user_factory, good):
    """Har baholanadigan node o'z vaqtida topshiriladi; 4-kun incident'i 3-kun kodi baliga bog'liq."""
    defn = _load(CONTENT / f"{WEEK}.yaml")
    run = await _start(db_session, test_user_factory, CONTENT / f"{WEEK}.yaml", f"week-{good}@example.com")
    fixed = sorted(
        (n for n in defn.nodes if n.day is not None and n.is_graded),
        key=lambda n: (n.day, n.at),
    )
    for n in fixed:
        at = T(n.at, WEEK_DAYS[n.day])
        await _step(db_session, run, at)
        event = (await _events(db_session, run))[n.id]
        if event.status == RunEventStatus.SKIPPED:
            continue
        assert event.status == RunEventStatus.DELIVERED, n.id
        reply_at = at + (T("09:05") - T("09:00"))
        if n.type == NodeType.DECISION:
            grade = "correct" if good else "wrong"
            await decide(db_session, run, n.id, next(o.key for o in n.options if o.grade == grade), reply_at)
            await db_session.commit()
        else:
            await _answer(db_session, run, n.id, reply_at, 40 if (n.id == "implement_cancel" and not good) else 80)

    await db_session.refresh(run)
    events = await _events(db_session, run)
    assert run.status == RunStatus.COMPLETED
    assert events["incident_refund_timeout"].status == (RunEventStatus.SUBMITTED if good else RunEventStatus.SKIPPED)
    assert events["incident_double_refund"].status == (RunEventStatus.SKIPPED if good else RunEventStatus.SUBMITTED)
    flagged = RunEventStatus.SKIPPED if good else RunEventStatus.DELIVERED
    assert {events[m].status for m in ("lead_on_scope", "lead_on_friday")} == {flagged}
    assert sorted(run.flags) == ([] if good else ["friday_deploy", "scope_creep"])
    assert events["mentor_code_note"].status == RunEventStatus.DELIVERED
