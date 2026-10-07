"""
Run javobini baholash (CONTRACT.md §9.6) — arq job ichida chaqiriladi.

Avval yashirin testlar (`checks`, §19.4) alohida runner'da, keyin rubrika
bo'yicha LLM baholash (`ai.evaluator.evaluate_rubric`): har mezonga ball va
dalil → `submissions.rubric_scores`; xom ball mezon og'irliklaridan va test
ulushidan.

Jarimalar kodda (§9.6): `late` → ×(1 − late_penalty), har ishlatilgan hint →
−hint_penalty. Yakuniy ball `submissions.ai_score`ga yoziladi (Universitet
portali statistikasi shu ustundan).
"""

from __future__ import annotations

import ast
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.evaluator import evaluate_rubric
from app.ai.guardrail import validate_submission_content
from app.core.sandbox import SandboxDisabled, SandboxUnavailable, run_tests
from app.models.enums import AIEvalStatus
from app.models.scenario import Run, RunEvent, ScenarioVersion, UploadedFile
from app.models.simulation import Submission
from app.scenario.engine import Note, definition_for
from app.scenario.schema import Checks, Node

log = logging.getLogger(__name__)

MAX_EVAL_TRIES = 3

DAY_END_BRIEF = "Kun yakuni hisoboti: nima qilindi, qanday muammolar bo'ldi, ertangi reja."


# Test ballga kiradigan holatlar; qolganlarida (runner yo'q) faqat rubrika
SCORED_CHECKS = {"ok", "error", "timeout", "no_code"}


def penalty_factor(node: Node, late: bool, hints_used: int) -> float:
    factor = (1 - node.late_penalty) if late else 1.0
    return max(0.0, factor * (1 - node.hint_penalty * hints_used))


def _test_names(tests: str) -> list[str]:
    return [n.name for n in ast.parse(tests).body if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]


async def run_checks(checks: Checks, code: str | None) -> dict:
    """`check_results` (§19.4); runner ishlamasa `SandboxUnavailable` o'tkaziladi."""
    names = _test_names(checks.tests)
    if not code:
        return {"status": "no_code", "passed": 0, "total": len(names), "failed": names}
    try:
        r = await run_tests(code, checks.tests, checks.module)
    except SandboxDisabled:
        return {"status": "disabled", "passed": 0, "total": len(names), "failed": []}
    return {
        "status": r["status"], "passed": r["passed"], "total": r["total"],
        "failed": [t["name"] for t in r["tests"] if not t["ok"]],
    }


def checks_line(results: dict) -> str:
    """LLM baholovchi uchun qisqa satr — test kodi emas, faqat natija."""
    if results["status"] not in SCORED_CHECKS:
        return ""
    line = f"[Avtomatik testlar: {results['passed']}/{results['total']} o'tdi"
    if results["status"] == "no_code":
        line += "; kod topshirilmagan"
    elif results["status"] != "ok":
        line += f"; kod ishga tushmadi ({results['status']})"
    if results["failed"]:
        line += "; yiqilgan: " + ", ".join(results["failed"])
    return line + "]"


def combined_score(rubric: float, node: Node, results: dict | None) -> float:
    """Xom ball (§19.4): `(1 − w) × rubrika + w × test ulushi`."""
    if not node.checks or not results or results["status"] not in SCORED_CHECKS or not results["total"]:
        return rubric
    w = node.checks.weight
    return (1 - w) * rubric + w * 100 * results["passed"] / results["total"]


async def evaluate_run_submission(
    db: AsyncSession,
    submission_id,
    now: datetime,
    job_try: int = 1,
    evaluate=evaluate_rubric,
) -> tuple[list[Note], bool]:
    """
    `(bildirishnomalar, qayta_urinish_kerakmi)` qaytaradi va commit qiladi.
    Allaqachon baholangan yoki Run'ga tegishli bo'lmagan submission — o'tkazib yuboriladi.
    """
    sub = await db.get(Submission, submission_id)
    if sub is None or sub.run_event_id is None or sub.ai_eval_status in (
        AIEvalStatus.COMPLETED, AIEvalStatus.FAILED_PERMANENT,
    ):
        return [], False

    event = await db.get(RunEvent, sub.run_event_id)
    run = (await db.execute(
        select(Run).where(Run.id == sub.run_id).options(
            selectinload(Run.scenario_version).selectinload(ScenarioVersion.scenario)
        )
    )).scalars().one()
    node = definition_for(run.scenario_version).node(event.node_id)

    answer = sub.content
    if sub.link_url:
        answer += f"\n\nLink: {sub.link_url}"
    if sub.file_id:
        f = await db.get(UploadedFile, sub.file_id)
        answer += f"\n\n[Attached file: {f.original_name if f else 'unknown'}]"
    answer = answer.strip()

    def note(status: AIEvalStatus) -> Note:
        return Note(run.id, "submission_evaluated", {
            "node_id": node.id, "attempt": sub.attempt, "status": status.value,
            "score": sub.ai_score, "feedback": sub.ai_feedback, "checks": public_checks(sub.check_results),
        })

    if not await validate_submission_content(answer):
        sub.ai_eval_status = AIEvalStatus.FAILED_PERMANENT
        sub.ai_feedback = "Javob avtomatik tekshiruvdan o'tmadi."
        sub.evaluated_at = now
        await db.commit()
        return [note(sub.ai_eval_status)], False

    # Testlar bir marta: AI qayta urinishida runner qayta chaqirilmaydi
    if node.checks and (sub.check_results is None or sub.check_results["status"] == "unavailable"):
        try:
            sub.check_results = await run_checks(node.checks, sub.code)
        except SandboxUnavailable as exc:
            log.warning("checks: %s (submission %s, urinish %s)", exc, sub.id, job_try)
            if job_try < MAX_EVAL_TRIES:
                sub.ai_eval_status = AIEvalStatus.QUEUED_RETRY
                await db.commit()
                return [], True
            names = _test_names(node.checks.tests)
            sub.check_results = {"status": "unavailable", "passed": 0, "total": len(names), "failed": []}
    if sub.check_results and (line := checks_line(sub.check_results)):
        answer = f"{answer}\n\n{line}"

    result = await evaluate(
        node.brief or DAY_END_BRIEF,
        answer,
        node.rubric,
        reference_answer=node.reference_answer,
        sector=run.scenario_version.scenario.sector,
    )

    if result is None:
        if job_try >= MAX_EVAL_TRIES:
            sub.ai_eval_status = AIEvalStatus.FAILED_PERMANENT
            sub.ai_feedback = f"AI baholash {MAX_EVAL_TRIES} urinishdan keyin muvaffaqiyatsiz."
            sub.evaluated_at = now
            await db.commit()
            return [note(sub.ai_eval_status)], False
        sub.ai_eval_status = AIEvalStatus.QUEUED_RETRY
        await db.commit()
        return [], True

    factor = penalty_factor(node, sub.late, event.hints_used)
    raw = combined_score(result.score, node, sub.check_results)
    sub.ai_score = round(raw * factor, 1)
    sub.ai_feedback = result.short_feedback
    sub.rubric_scores = {**result.as_json(), "combined_score": round(raw, 1), "penalty_factor": round(factor, 3)}
    sub.ai_eval_status = AIEvalStatus.COMPLETED
    sub.evaluated_at = now
    await db.commit()
    return [note(sub.ai_eval_status)], False


def public_checks(results: dict | None) -> dict | None:
    """Talabaga ko'rinadigan qism (§19.3): faqat sonlar va yiqilgan test nomlari."""
    if not results or results["status"] not in SCORED_CHECKS:
        return None
    return {"status": results["status"], "passed": results["passed"], "total": results["total"], "failed": results["failed"]}
