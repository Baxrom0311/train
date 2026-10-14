"""`backend/content/scenarios/` kontenti: sxema, sifat qoidalari va to'liq kun/hafta/jamoa o'tishi (CONTRACT.md §9.11, §29)."""
import uuid
from datetime import timedelta
from pathlib import Path

import pytest
import yaml

from app.ai.reports import FinalSummary
from app.models.enums import AIEvalStatus, NodeType, RunEventStatus, RunStatus, Sector
from app.models.scenario import RunTeam, RunTeamMember
from app.scenario.conditions import FlagSet, ScoreGte, iter_leaves, referenced_nodes, score_nodes
from app.scenario.engine import Answer, advance, create_run, decide, submit_answer
from app.scenario.importer import import_scenario, publish_version
from app.scenario.reports import write_final_report
from app.scenario.schema import ANSWER_TYPES, PersonaKind, ScenarioDefinition, scenario_warnings
from app.scenario.team import assign_roles
from tests.test_runs_engine import T, _events, _step

CONTENT = Path(__file__).resolve().parents[1] / "content" / "scenarios"
FILES = sorted(CONTENT.glob("*.yaml"))


def _load(path: Path) -> ScenarioDefinition:
    return ScenarioDefinition.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def _kind(d: ScenarioDefinition) -> str:
    return "team" if d.team is not None else ("week" if d.duration_days == 5 else "day")


DEFS = {p.stem: _load(p) for p in FILES}
WEEKS = sorted(slug for slug, d in DEFS.items() if _kind(d) == "week")
TEAMS = sorted(slug for slug, d in DEFS.items() if _kind(d) == "team")


def test_content_covers_every_sector():
    """§9.11: har sohada 1 kunlik, haftalik va jamoaviy ssenariy; har biri o'z to'liq o'tish testida."""
    by_sector: dict[Sector, list[str]] = {}
    for d in DEFS.values():
        assert d.duration_days in (1, 5) and (d.team is None or d.duration_days == 1), d.slug
        by_sector.setdefault(d.sector, []).append(_kind(d))
    assert {s: sorted(k) for s, k in by_sector.items()} == {s: ["day", "team", "week"] for s in Sector}
    assert {slug for slug, d in DEFS.items() if _kind(d) == "day"} == set(PATHS)


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


WEEK_DAYS = {1: 7, 2: 8, 3: 9, 4: 12, 5: 13}   # chorshanba → keyingi seshanba (dam olish kunlari o'tkaziladi)


def _week_shape(defn: ScenarioDefinition):
    """Haftalik skelet: kalit task, unga bog'liq 4-kun incident juftligi, flag xabarlari, mentor izohi."""
    (strong,) = [n for n in defn.nodes if n.is_graded and any(isinstance(leaf, ScoreGte) for leaf in iter_leaves(n.when))]
    (key,) = score_nodes(strong.when)
    (weak,) = [n for n in defn.nodes if n.is_graded and n is not strong and key in referenced_nodes(n.when)]
    flagged = {
        n.id: leaf.flag for n in defn.nodes if n.type == NodeType.MESSAGE
        for leaf in iter_leaves(n.when) if isinstance(leaf, FlagSet)
    }
    mentor_notes = [n.id for n in defn.nodes if n.after and n.after.node == key and n.from_ == defn.mentor.key]
    return key, weak.id, strong.id, flagged, mentor_notes


@pytest.mark.parametrize("slug", WEEKS)
def test_week_shape(slug):
    defn = DEFS[slug]
    key, weak, strong, flagged, mentor_notes = _week_shape(defn)
    assert (defn.node(weak).day, defn.node(weak).at) == (defn.node(strong).day, defn.node(strong).at)
    assert defn.node(weak).day == 4 and defn.node(key).day < 4
    wrong_flags = {o.flag for n in defn.nodes if n.type == NodeType.DECISION for o in n.options if o.grade == "wrong"}
    assert len(wrong_flags) >= 2 and None not in wrong_flags
    assert set(flagged.values()) == wrong_flags, "har xato qaror rahbar xabarini chaqiradi"
    assert mentor_notes, "kalit task'dan keyin mentor izohi"
    for day in range(1, 6):
        assert defn.node(f"standup_d{day}").day == day and defn.node(f"day{day}_end").day == day
    # nisbiy (`after`) node'lar haftalikda faqat xabar — to'liq hafta testi ularni kutmaydi
    assert all(n.type == NodeType.MESSAGE for n in defn.nodes if n.after)


@pytest.mark.parametrize("good", [True, False], ids=["strong", "weak"])
@pytest.mark.parametrize("slug", WEEKS)
async def test_full_week(db_session, test_user_factory, slug, good):
    """Har baholanadigan node o'z vaqtida topshiriladi; 4-kun incident'i kalit task baliga bog'liq."""
    defn = DEFS[slug]
    key, weak, strong, flagged, mentor_notes = _week_shape(defn)
    run = await _start(db_session, test_user_factory, CONTENT / f"{slug}.yaml", f"{slug}-{good}@example.com")
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
            await _answer(db_session, run, n.id, reply_at, 40 if (n.id == key and not good) else 80)

    await db_session.refresh(run)
    events = await _events(db_session, run)
    assert run.status == RunStatus.COMPLETED
    assert events[strong].status == (RunEventStatus.SUBMITTED if good else RunEventStatus.SKIPPED)
    assert events[weak].status == (RunEventStatus.SKIPPED if good else RunEventStatus.SUBMITTED)
    assert {events[m].status for m in flagged} == {RunEventStatus.SKIPPED if good else RunEventStatus.DELIVERED}
    assert sorted(run.flags) == ([] if good else sorted(set(flagged.values())))
    assert all(events[m].status == RunEventStatus.DELIVERED for m in mentor_notes)


# ── Jamoaviy ssenariylar (§29) ────────────────────────────────────────


@pytest.mark.parametrize("slug", TEAMS)
def test_team_shape(slug):
    """Jamoa skeleti: umumiy standup, qaror va kun yakuni; har rolga task va incident; rollararo bog'liqlik."""
    defn = DEFS[slug]
    roles = [r.key for r in defn.team.roles]
    assert len(roles) == 3 and defn.team.min_size == 2
    assert all(r.summary for r in defn.team.roles)
    graded = [n for n in defn.nodes if n.is_graded]
    for kind in (NodeType.TASK, NodeType.INCIDENT):
        assert {n.role for n in graded if n.type == kind and n.role} == set(roles), kind
    shared = {n.type for n in graded if n.role is None}
    assert shared == {NodeType.TASK, NodeType.DECISION, NodeType.DAY_END}
    (handoff,) = [n for n in graded if n.after is not None]
    trigger = defn.node(handoff.after.node)
    assert handoff.after.event == "submitted" and trigger.role and handoff.role and trigger.role != handoff.role


def _grid():
    """09:00–17:45 har 15 daqiqa (tushlikdan tashqari)."""
    for h in (9, 10, 11, 12, 14, 15, 16, 17):
        for m in (0, 15, 30, 45):
            yield f"{h:02d}:{m:02d}"


@pytest.mark.parametrize("good", [True, False], ids=["strong", "weak"])
@pytest.mark.parametrize("slug", TEAMS)
async def test_full_team_day(db_session, test_user_factory, slug, good):
    """Uch a'zo har biri o'z rolida: hamma ish o'z vaqtida, hisobotda har kimning hissasi."""
    defn = DEFS[slug]
    roles = [r.key for r in defn.team.roles]
    version, _ = await import_scenario(db_session, defn)
    await publish_version(db_session, version)
    users = []
    for i, name in enumerate(("Ali", "Bobur", "Charos")):
        u = await test_user_factory(f"{slug}-{good}-{i}@example.com", "pass")
        u.full_name = name
        users.append(u)
    team = RunTeam(id=uuid.uuid4(), scenario_id=version.scenario_id, scenario_version_id=version.id,
                   captain_id=users[0].id, invite_code=uuid.uuid4().hex[:8].upper(), status="started",
                   created_at=T("08:00"), started_at=T("08:00"))
    db_session.add(team)
    await db_session.flush()
    holdings = assign_roles(roles, [(u.id, role) for u, role in zip(users, roles)])
    holder = {role: u for u in users for role in holdings[u.id]}
    for i, u in enumerate(users):
        db_session.add(RunTeamMember(team_id=team.id, user_id=u.id, roles=holdings[u.id],
                                     joined_at=T("08:00") + timedelta(seconds=i)))
    run, _ = await create_run(db_session, users[0].id, version, T("09:00"), T("09:00"), team_id=team.id,
                              participants=[u.id for u in users])
    await db_session.commit()

    for hhmm in _grid():
        now = T(hhmm)
        await _step(db_session, run, now)
        reply_at = now + timedelta(minutes=1)
        for e in (await _events(db_session, run)).values():
            node = defn.node(e.node_id)
            if e.status != RunEventStatus.DELIVERED or not node.is_graded:
                continue
            actor = holder[node.role] if node.role else users[1]
            if node.type == NodeType.DECISION:
                grade = "correct" if good else "wrong"
                option = next(o.key for o in node.options if o.grade == grade)
                await decide(db_session, run, node.id, option, reply_at, actor_id=actor.id)
                await db_session.commit()
            else:
                sub, _ = await submit_answer(db_session, run, node.id, Answer(text="javob"), reply_at, actor_id=actor.id)
                sub.ai_eval_status = AIEvalStatus.COMPLETED
                sub.ai_score = 85 if good else 55
                sub.evaluated_at = reply_at
                await db_session.commit()

    await db_session.refresh(run)
    events = await _events(db_session, run)
    assert run.status == RunStatus.COMPLETED
    assert not [e.node_id for e in events.values() if e.status == RunEventStatus.MISSED]
    decision = next(n for n in defn.nodes if n.type == NodeType.DECISION)
    wrong_flag = next(o.flag for o in decision.options if o.grade == "wrong")
    lead = [n.id for n in defn.nodes for leaf in iter_leaves(n.when) if isinstance(leaf, FlagSet) and leaf.flag == wrong_flag]
    assert lead and {events[m].status for m in lead} == {RunEventStatus.SKIPPED if good else RunEventStatus.DELIVERED}

    async def final(tasks, competencies, messages, completed):
        return FinalSummary(summary="Jamoa", strengths=["a"], improvements=["b"], initiative_score=60)

    assert await write_final_report(db_session, run.id, T("18:00"), summarize=final)
    await db_session.refresh(run)
    report = run.final_report
    assert report["certificate"] is False and not report["incomplete"]
    for t in report["tasks"]:
        node = defn.node(t["node_id"])
        if node.role:
            assert t["role"] == node.role and t["by"] == str(holder[node.role].id), node.id
    assert [r["key"] for r in report["team"]["roles"]] == roles
    members = report["team"]["members"]
    assert all(m["assigned"] >= 2 and m["submitted"] == m["assigned"] and m["on_time_rate"] == 100.0 for m in members)
    assert sum(m["share"] for m in members) == pytest.approx(100, abs=0.2)
