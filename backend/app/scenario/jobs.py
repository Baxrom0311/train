"""
Ssenariy dvigatelining arq job'lari (CONTRACT.md §9.8). `WorkerSettings`ga
`app/ai/worker.py` ulaydi (§9.10, Modul 2).

- `deliver_due_events` — har daqiqa: `advance`, bildirishnomalar, va
  navbatga tushmay qolgan `pending` javoblarni qayta navbatga qo'yish.
- `evaluate_run_submission_job` — bitta Run javobini baholash.
- `sync_work_holidays_job` — haftalik bayramlar sinxronizatsiyasi.
"""

import logging
from datetime import datetime, timedelta, timezone

from arq import Retry
from sqlalchemy import select

from app.models.enums import AIEvalStatus
from app.models.simulation import Submission
from app.scenario import notify
from app.scenario.engine import advance
from app.scenario.evaluation import evaluate_run_submission
from app.scenario.holidays import sync_work_holidays

log = logging.getLogger(__name__)

EVAL_JOB = "evaluate_run_submission_job"
# Shuncha vaqt `pending` turgan javob navbatga tushmagan deb hisoblanadi
STALE_PENDING = timedelta(minutes=5)


def eval_job_id(submission_id) -> str:
    return f"run-eval:{submission_id}"


async def enqueue_evaluation(arq_pool, submission_id) -> None:
    try:
        await arq_pool.enqueue_job(EVAL_JOB, str(submission_id), _job_id=eval_job_id(submission_id))
    except Exception as exc:  # noqa: BLE001 — cron qayta navbatga qo'yadi
        log.error("baholash navbatga qo'yilmadi (%s): %s", submission_id, exc)


def _sessions(ctx: dict):
    if "session_factory" in ctx:
        return ctx["session_factory"]
    from app.database import AsyncSessionLocal
    return AsyncSessionLocal


async def deliver_due_events(ctx: dict) -> int:
    now = datetime.now(timezone.utc)
    async with _sessions(ctx)() as db:
        notes = await advance(db, now)
        await db.commit()
        stale = (await db.execute(
            select(Submission.id).where(
                Submission.run_event_id.is_not(None),
                Submission.ai_eval_status == AIEvalStatus.PENDING,
                Submission.submitted_at <= now - STALE_PENDING,
            )
        )).scalars().all()
    await notify.publish(notes)
    for sid in stale:
        await enqueue_evaluation(ctx["redis"], sid)
    return len(notes)


async def evaluate_run_submission_job(ctx: dict, submission_id: str) -> None:
    job_try = ctx.get("job_try", 1)
    async with _sessions(ctx)() as db:
        notes, retry = await evaluate_run_submission(
            db, submission_id, datetime.now(timezone.utc), job_try=job_try
        )
    await notify.publish(notes)
    if retry:
        raise Retry(defer=2 ** job_try)


async def sync_work_holidays_job(ctx: dict) -> int:
    async with _sessions(ctx)() as db:
        count = await sync_work_holidays(db, datetime.now(timezone.utc).date())
        await db.commit()
    log.info("work_holidays: %d ta auto sana yozildi", count)
    return count
