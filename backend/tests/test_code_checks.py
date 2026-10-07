"""
Kod tekshiruvi (CONTRACT.md §19): runner, `checks` sxemasi, baholashga ulanish.

Eng muhim qoidalar: talaba kodi faqat runner'da; natijani `print` bilan
soxtalashtirib bo'lmaydi; runner ishlamasa — qayta urinish, oxirida faqat
rubrika; talabaga test kodi emas, faqat yiqilgan test nomlari.
"""
import json
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.ai.evaluator import CriterionScore, RubricResult
from app.ai.llm import LLMResult
from app.core.sandbox import SandboxUnavailable
from app.models.enums import AIEvalStatus
from app.models.simulation import Submission
from app.models.user import User
from app.scenario import evaluation
from app.scenario.engine import Answer, create_run, submit_answer
from app.scenario.evaluation import checks_line, combined_score, evaluate_run_submission
from app.scenario.importer import import_scenario, publish_version
from app.scenario.mentor import student_work_lines
from app.scenario.schema import Checks, Node, ScenarioDefinition
from tests.test_runs_engine import FIXTURE, T, _step

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "sandbox"))
import runner  # noqa: E402

TESTS = """from solution import add
def test_ok():
    assert add(1, 2) == 3
def test_negative():
    assert add(-2, 2) == 0
def test_type():
    assert add(None, 1) is None
"""


# fixture'dagi bug_orders + yashirin testlar (§19.3)
HIDDEN = """from solution import total_amount
def test_refund_has_no_amount():
    assert total_amount([{"amount": None, "status": "refunded"}]) == 0
def test_sums_paid_orders():
    assert total_amount([{"amount": 5, "status": "paid"}, {"amount": 7, "status": "paid"}]) == 12
"""


def _defn() -> ScenarioDefinition:
    import yaml
    data = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    node = next(n for n in data["nodes"] if n["id"] == "bug_orders")
    node["checks"] = {"tests": HIDDEN}
    return ScenarioDefinition.model_validate(data)


@pytest.fixture
async def setup(db_session, test_user_factory):
    async def _setup(start):
        user = await test_user_factory(f"code{start.timestamp():.0f}@example.com", "pass")
        version, _ = await import_scenario(db_session, _defn())
        await publish_version(db_session, version)
        run, info = await create_run(db_session, user.id, version, start, start)
        await db_session.commit()
        return run, info
    return _setup


# ── Runner ───────────────────────────────────────────────────────────


def test_runner_counts_passed_and_failed():
    r = runner.execute("def add(a, b):\n    print('debug')\n    return a + b", TESTS)
    assert (r["status"], r["passed"], r["total"]) == ("ok", 2, 3)
    assert [t["name"] for t in r["tests"] if not t["ok"]] == ["test_type"]
    assert "debug" in r["stdout"]


def test_runner_broken_code_fails_every_test():
    r = runner.execute("def add(a, b) return", TESTS)
    assert (r["status"], r["passed"], r["total"]) == ("error", 0, 3)


@pytest.mark.parametrize("code", [
    # natija yozilmasdan jarayon tugaydi
    "import os\nos._exit(0)",
    # soxta natija satri — nonce'siz qabul qilinmaydi
    'print("\\nx {\\"status\\": \\"ok\\", \\"tests\\": [{\\"name\\": \\"test_ok\\", \\"ok\\": true}]}")\nraise SystemExit',
])
def test_runner_result_cannot_be_forged(code):
    r = runner.execute(code, TESTS)
    assert r["passed"] == 0 and r["total"] == 3


def test_runner_limits():
    assert runner.execute("while True:\n    pass", TESTS, timeout=1)["status"] == "timeout"
    assert runner.execute("x = 'a' * (10 ** 9)")["status"] == "error"          # 256 MB
    assert runner.execute("print(sum(range(10)))")["stdout"] == "45\n"
    assert runner.execute("while True:\n    pass", timeout=99)["status"] == "timeout"  # skript ≤ 3 s


@pytest.fixture
def server(monkeypatch):
    monkeypatch.setattr(runner, "TOKEN", "t0ken")
    srv = ThreadingHTTPServer(("127.0.0.1", 0), runner.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def _post(url, body, token="t0ken"):
    req = urllib.request.Request(f"{url}/run", data=json.dumps(body).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_runner_http(server):
    assert _post(server, {"code": "print(1)"}, token="wrong")[0] == 401
    assert _post(server, {"code": "x", "module": "../etc"})[0] == 400
    assert _post(server, {"code": "x", "module": "hidden_tests"})[0] == 400
    assert _post(server, {"code": "x", "tests": "def broken("})[0] == 400
    status, body = _post(server, {"code": "def add(a, b):\n    return a + b", "tests": TESTS})
    assert status == 200 and (body["passed"], body["total"]) == (2, 3)
    with urllib.request.urlopen(f"{server}/health", timeout=5) as r:
        assert json.loads(r.read()) == {"ok": True}


def test_runner_busy(server, monkeypatch):
    monkeypatch.setattr(runner, "SLOTS", threading.BoundedSemaphore(1))
    runner.SLOTS.acquire()
    try:
        assert _post(server, {"code": "print(1)"}) == (503, {"error": "busy"})
    finally:
        runner.SLOTS.release()


# ── Sxema ────────────────────────────────────────────────────────────


def test_checks_schema():
    with pytest.raises(ValidationError, match="test_"):
        Checks(tests="def helper():\n    pass")
    with pytest.raises(ValidationError, match="sintaksis"):
        Checks(tests="def test_x(:")
    with pytest.raises(ValidationError):
        Checks(tests=TESTS, module="../x")
    with pytest.raises(ValidationError, match="code"):
        Node.model_validate({
            "id": "t", "type": "task", "day": 1, "at": "09:00", "brief": "b", "answer_types": ["text"],
            "due_in_minutes": 30, "checks": {"tests": TESTS},
        })


def test_score_combination_and_llm_line():
    node = _defn().node("bug_orders")          # checks.weight = 0.5 (standart)
    ok = {"status": "ok", "passed": 1, "total": 2, "failed": ["test_sums_paid_orders"]}
    assert combined_score(80.0, node, ok) == pytest.approx(65.0)        # 0.5×80 + 0.5×50
    assert combined_score(80.0, node, {**ok, "status": "unavailable"}) == 80.0
    assert combined_score(80.0, node, {**ok, "status": "disabled"}) == 80.0
    assert checks_line(ok) == "[Avtomatik testlar: 1/2 o'tdi; yiqilgan: test_sums_paid_orders]"
    assert checks_line({**ok, "status": "unavailable"}) == ""


# ── Baholash ─────────────────────────────────────────────────────────


def _rubric(score=80.0):
    calls = []

    async def evaluate(brief, answer, rubric, *, reference_answer, sector):
        calls.append(answer)
        return RubricResult(
            criteria=[CriterionScore(id=c.id, score=score) for c in rubric], score=score, short_feedback="Yaxshi",
            llm=LLMResult(text="{}", data=None, provider="fake", model="fake"),
        )
    return evaluate, calls


async def _submitted(db, setup, answer):
    run, _ = await setup(T("09:00"))
    await _step(db, run, T("09:30"))
    sub, _ = await submit_answer(db, run, "bug_orders", answer, T("09:40"))
    await db.commit()
    return run, sub


async def _stored(db, sub_id):
    s = await db.get(Submission, sub_id)
    await db.refresh(s)
    return s


CODE = "def total_amount(rows):\n    return sum(r['amount'] for r in rows)"


async def test_evaluation_runs_hidden_tests(db_session, setup, monkeypatch):
    sent = []

    async def fake_run_tests(code, tests, module):
        sent.append((code, module))
        return runner.execute(code, tests, module)       # haqiqiy harness, runner konteynerisiz
    monkeypatch.setattr(evaluation, "run_tests", fake_run_tests)
    evaluate, calls = _rubric(80.0)

    run, sub = await _submitted(db_session, setup, Answer(text="Sabab: None summa", code=CODE))
    notes, retry = await evaluate_run_submission(db_session, sub.id, T("09:41"), evaluate=evaluate)

    stored = await _stored(db_session, sub.id)
    assert not retry and stored.code == CODE and sent == [(CODE, "solution")]
    # refund qatori None → TypeError; to'langanlar yig'indisi to'g'ri
    assert stored.check_results == {
        "status": "ok", "passed": 1, "total": 2, "failed": ["test_refund_has_no_amount"],
    }
    assert stored.ai_score == 65.0 and stored.rubric_scores["combined_score"] == 65.0
    assert calls[0].endswith("[Avtomatik testlar: 1/2 o'tdi; yiqilgan: test_refund_has_no_amount]")
    assert notes[0].data["checks"] == {
        "status": "ok", "passed": 1, "total": 2, "failed": ["test_refund_has_no_amount"],
    }


async def test_evaluation_without_code_scores_zero_tests(db_session, setup, monkeypatch):
    async def never(*args):
        raise AssertionError("kod yo'q — runner chaqirilmasin")
    monkeypatch.setattr(evaluation, "run_tests", never)
    evaluate, _ = _rubric(80.0)
    _, sub = await _submitted(db_session, setup, Answer(text="faqat matn"))
    await evaluate_run_submission(db_session, sub.id, T("09:41"), evaluate=evaluate)
    stored = await _stored(db_session, sub.id)
    assert stored.check_results["status"] == "no_code" and stored.ai_score == 40.0


async def test_evaluation_without_runner_uses_rubric_only(db_session, setup):
    # testlarda SANDBOX_URL bo'sh — lokal rejim, yashirin testlar o'chiq
    evaluate, calls = _rubric(80.0)
    _, sub = await _submitted(db_session, setup, Answer(code=CODE))
    await evaluate_run_submission(db_session, sub.id, T("09:41"), evaluate=evaluate)
    stored = await _stored(db_session, sub.id)
    assert stored.check_results["status"] == "disabled" and stored.ai_score == 80.0
    assert "Avtomatik testlar" not in calls[0]


async def test_runner_down_retries_then_rubric_only(db_session, setup, monkeypatch):
    attempts = []

    async def down(*args):
        attempts.append(1)
        raise SandboxUnavailable("runner 503 qaytardi")
    monkeypatch.setattr(evaluation, "run_tests", down)
    evaluate, calls = _rubric(80.0)
    _, sub = await _submitted(db_session, setup, Answer(code=CODE))

    _, retry = await evaluate_run_submission(db_session, sub.id, T("09:41"), job_try=1, evaluate=evaluate)
    assert retry and not calls
    assert (await _stored(db_session, sub.id)).ai_eval_status == AIEvalStatus.QUEUED_RETRY

    _, retry = await evaluate_run_submission(db_session, sub.id, T("09:45"), job_try=3, evaluate=evaluate)
    stored = await _stored(db_session, sub.id)
    assert not retry and len(attempts) == 2
    assert stored.check_results["status"] == "unavailable" and stored.ai_score == 80.0


async def test_ai_retry_does_not_rerun_tests(db_session, setup, monkeypatch):
    runs = []

    async def fake_run_tests(code, tests, module):
        runs.append(1)
        return runner.execute(code, tests, module)
    monkeypatch.setattr(evaluation, "run_tests", fake_run_tests)

    async def ai_down(*args, **kwargs):
        return None
    _, sub = await _submitted(db_session, setup, Answer(code=CODE))
    _, retry = await evaluate_run_submission(db_session, sub.id, T("09:41"), job_try=1, evaluate=ai_down)
    assert retry
    evaluate, _ = _rubric(80.0)
    await evaluate_run_submission(db_session, sub.id, T("09:45"), job_try=2, evaluate=evaluate)
    assert len(runs) == 1 and (await _stored(db_session, sub.id)).ai_score == 65.0


async def test_student_sees_only_test_names(client, db_session, setup, monkeypatch):
    async def fake_run_tests(code, tests, module):
        return runner.execute(code, tests, module)
    monkeypatch.setattr(evaluation, "run_tests", fake_run_tests)
    evaluate, _ = _rubric(80.0)
    run, sub = await _submitted(db_session, setup, Answer(code=CODE))
    await evaluate_run_submission(db_session, sub.id, T("09:41"), evaluate=evaluate)

    user = await db_session.get(User, run.user_id)
    login = await client.post("/api/v1/auth/login", data={"username": user.email, "password": "pass"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    detail = (await client.get(f"/api/v1/runs/{run.id}", headers=headers)).json()
    event = next(e for e in detail["events"] if e["node_id"] == "bug_orders")
    assert event["last_checks"] == {"status": "ok", "passed": 1, "total": 2, "failed": ["test_refund_has_no_amount"]}
    # test kodi va kutilgan qiymatlar hech qayerda yo'q
    assert "total_amount([" not in json.dumps(detail)


async def test_mentor_sees_test_summary_not_code(db_session, setup, monkeypatch):
    async def fake_run_tests(code, tests, module):
        return runner.execute(code, tests, module)
    monkeypatch.setattr(evaluation, "run_tests", fake_run_tests)
    evaluate, _ = _rubric(80.0)
    run, sub = await _submitted(db_session, setup, Answer(code=CODE))
    await evaluate_run_submission(db_session, sub.id, T("09:41"), evaluate=evaluate)

    from app.models.scenario import RunEvent
    from sqlalchemy import select
    events = (await db_session.execute(select(RunEvent).where(RunEvent.run_id == run.id))).scalars().all()
    [line] = student_work_lines(_defn(), events, [await _stored(db_session, sub.id)])
    assert "Avtomatik testlar: 1/2 o'tdi; yiqilgan: test_refund_has_no_amount" in line
    assert "total_amount([" not in line
