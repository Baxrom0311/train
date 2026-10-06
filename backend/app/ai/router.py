import random
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.simulation import Submission
from app.ai.guardrail import validate_submission_content

async def evaluate_submission(submission: Submission, db: AsyncSession) -> None:
    is_valid = await validate_submission_content(submission.content)
    if not is_valid:
        submission.ai_eval_status = "failed_permanent"
        submission.ai_feedback = "Content failed guardrail validation."
        submission.evaluated_at = datetime.utcnow()
        await db.commit()
        return

    try:
        submission.ai_score = round(random.uniform(60.0, 95.0), 1)
        submission.ai_feedback = "Good job on this task. Here are a few things to improve..."
        submission.ai_eval_status = "completed"
        submission.evaluated_at = datetime.utcnow()
        await db.commit()
    except Exception:
        submission.ai_eval_status = "queued_retry"
        await db.commit()
