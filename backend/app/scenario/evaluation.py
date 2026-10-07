"""
Run javobini baholash (CONTRACT.md §9.6) — arq job ichida chaqiriladi.

Rubrika bo'yicha LLM baholash (`ai.evaluator.evaluate_rubric`): har mezonga
ball va dalil → `submissions.rubric_scores`; xom ball mezon og'irliklaridan.
Deterministik `checks` (sandbox) — keyingi bosqich.

Jarimalar kodda (§9.6): `late` → ×(1 − late_penalty), har ishlatilgan hint →
−hint_penalty. Yakuniy ball `submissions.ai_score`ga yoziladi (Universitet
portali statistikasi shu ustundan).
"""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.evaluator import evaluate_rubric
from app.ai.guardrail import validate_submission_content
from app.models.enums import AIEvalStatus
from app.models.scenario import Run, RunEvent, ScenarioVersion, UploadedFile
from app.models.simulation import Submission
from app.scenario.engine import Note, definition_for
from app.scenario.schema import Node

log = logging.getLogger(__name__)

MAX_EVAL_TRIES = 3

DAY_END_BRIEF = "Kun yakuni hisoboti: nima qilindi, qanday muammolar bo'ldi, ertangi reja."


def penalty_factor(node: Node, late: bool, hints_used: int) -> float:
    factor = (1 - node.late_penalty) if late else 1.0
    return max(0.0, factor * (1 - node.hint_penalty * hints_used))


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
            "score": sub.ai_score, "feedback": sub.ai_feedback,
        })

    if not await validate_submission_content(answer):
        sub.ai_eval_status = AIEvalStatus.FAILED_PERMANENT
        sub.ai_feedback = "Javob avtomatik tekshiruvdan o'tmadi."
        sub.evaluated_at = now
        await db.commit()
        return [note(sub.ai_eval_status)], False

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
    sub.ai_score = round(result.score * factor, 1)
    sub.ai_feedback = result.short_feedback
    sub.rubric_scores = {**result.as_json(), "penalty_factor": round(factor, 3)}
    sub.ai_eval_status = AIEvalStatus.COMPLETED
    sub.evaluated_at = now
    await db.commit()
    return [note(sub.ai_eval_status)], False
