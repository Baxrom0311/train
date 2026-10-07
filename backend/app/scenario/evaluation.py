"""
Run javobini baholash (CONTRACT.md §9.6) — arq job ichida chaqiriladi.

Vaqtinchalik (P4): mavjud AI zanjiri (`app.ai.router.run_ai_chain`) bilan
umumiy ball + qisqa feedback. Rubrika mezonlari bo'yicha tuzilgan baholash
(`ai.evaluate_rubric`) AI qatlami tayyor bo'lganda shu funksiya ichida
almashtiriladi; chaqiruvchilar o'zgarmaydi.

Jarimalar kodda (§9.6): `late` → ×(1 − late_penalty), har ishlatilgan hint →
−hint_penalty. Yakuniy ball `submissions.ai_score`ga yoziladi (Universitet
portali statistikasi shu ustundan).
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.guardrail import validate_submission_content
from app.ai.router import _pick_persona, run_ai_chain
from app.models.enums import AIEvalStatus
from app.models.scenario import Run, RunEvent, ScenarioVersion, UploadedFile
from app.models.simulation import Submission
from app.scenario.engine import Note, definition_for
from app.scenario.schema import Node

log = logging.getLogger(__name__)

MAX_EVAL_TRIES = 3

AIChain = Callable[[httpx.AsyncClient, str, str], Awaitable[tuple[float, str] | None]]


def penalty_factor(node: Node, late: bool, hints_used: int) -> float:
    factor = (1 - node.late_penalty) if late else 1.0
    return max(0.0, factor * (1 - node.hint_penalty * hints_used))


def build_prompt(node: Node, answer: str) -> str:
    lines = [
        "You are grading a student's work in a realistic job simulation.",
        f"TASK BRIEF:\n{node.brief or '(end-of-day report: what was done, blockers, plan for tomorrow)'}",
    ]
    if node.rubric:
        lines.append("RUBRIC (criterion: description, weight):")
        lines += [f"- {c.id}: {c.description} (weight {c.weight})" for c in node.rubric]
    if node.reference_answer:
        lines.append(f"REFERENCE ANSWER (for the grader only):\n{node.reference_answer}")
    lines += [
        f"STUDENT ANSWER:\n{answer}",
        "Return a JSON object with two keys:",
        '  "score": float from 0 to 100',
        '  "feedback": string (2-3 sentences of constructive feedback, in Uzbek)',
        "Return ONLY valid JSON, nothing else.",
    ]
    return "\n\n".join(lines)


async def evaluate_run_submission(
    db: AsyncSession,
    submission_id,
    now: datetime,
    job_try: int = 1,
    ai_chain: AIChain = run_ai_chain,
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
            "score": sub.ai_score, "feedback": sub.ai_feedback,
        })

    if not await validate_submission_content(answer):
        sub.ai_eval_status = AIEvalStatus.FAILED_PERMANENT
        sub.ai_feedback = "Javob avtomatik tekshiruvdan o'tmadi."
        sub.evaluated_at = now
        await db.commit()
        return [note(sub.ai_eval_status)], False

    persona = _pick_persona(run.scenario_version.scenario.sector)
    async with httpx.AsyncClient() as client:
        result = await ai_chain(client, persona.system_prompt, build_prompt(node, answer))

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

    raw, feedback = result
    raw = min(100.0, max(0.0, float(raw)))
    factor = penalty_factor(node, sub.late, event.hints_used)
    sub.ai_score = round(raw * factor, 1)
    sub.ai_feedback = feedback
    sub.rubric_scores = {"raw_score": raw, "penalty_factor": round(factor, 3)}
    sub.ai_eval_status = AIEvalStatus.COMPLETED
    sub.evaluated_at = now
    await db.commit()
    return [note(sub.ai_eval_status)], False
