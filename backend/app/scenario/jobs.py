"""
Ssenariy dvigatelining arq job'lari (CONTRACT.md §9.8). `WorkerSettings`ga
`app/ai/worker.py` ulaydi (§9.10, Modul 2).

- `deliver_due_events` — har daqiqa: `advance`, bildirishnomalar, va
  navbatga tushmay qolgan `pending` javoblarni qayta navbatga qo'yish.
- `evaluate_run_submission_job` — bitta Run javobini baholash, keyin mentor
  izohi (§9.13).
- `sync_work_holidays_job` — haftalik bayramlar sinxronizatsiyasi.
- `embed_document_chunks_job` — embedding'i yo'q RAG bo'laklarini to'ldirish.
- `day_report_job`, `final_report_job` — hisobotlar (§9.6); kerakli joylarni
  `deliver_due_events` topib navbatga qo'yadi, yozilmaguncha har daqiqa.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone

from arq import Retry
from sqlalchemy import select

from app.models.enums import AIEvalStatus
from app.models.simulation import Submission
from app.scenario import notify
from app.scenario.engine import Note, advance
from app.scenario.evaluation import evaluate_run_submission
from app.scenario.mentor import post_review
from app.scenario.holidays import sync_work_holidays
from app.scenario.rag import embed_pending_chunks
from app.scenario.reports import (
    pending_day_reports,
    pending_final_reports,
    write_day_report,
    write_final_report,
)

log = logging.getLogger(__name__)

EVAL_JOB = "evaluate_run_submission_job"
DAY_REPORT_JOB = "day_report_job"
FINAL_REPORT_JOB = "final_report_job"
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
        day_reports = await pending_day_reports(db)
        final_reports = await pending_final_reports(db)
    await notify.publish(notes)
    for sid in stale:
        await enqueue_evaluation(ctx["redis"], sid)
    # _job_id: navbatda/bajarilayotgan bo'lsa takrorlanmaydi (keep_result=0)
    for run_id, node_id in day_reports:
        await _enqueue(ctx["redis"], DAY_REPORT_JOB, str(run_id), node_id, _job_id=f"day-report:{run_id}:{node_id}")
    for run_id in final_reports:
        await _enqueue(ctx["redis"], FINAL_REPORT_JOB, str(run_id), _job_id=f"final-report:{run_id}")
    return len(notes)


async def _enqueue(arq_pool, name: str, *args, _job_id: str) -> None:
    try:
        await arq_pool.enqueue_job(name, *args, _job_id=_job_id)
    except Exception as exc:  # noqa: BLE001 — keyingi daqiqada qayta urinadi
        log.error("%s navbatga qo'yilmadi: %s", name, exc)


async def evaluate_run_submission_job(ctx: dict, submission_id: str) -> None:
    job_try = ctx.get("job_try", 1)
    async with _sessions(ctx)() as db:
        notes, retry = await evaluate_run_submission(
            db, submission_id, datetime.now(timezone.utc), job_try=job_try
        )
    # ball darhol ko'rinsin — mentor izohi (LLM) undan keyin
    await notify.publish(notes)
    if retry:
        raise Retry(defer=2 ** job_try)
    async with _sessions(ctx)() as db:
        note = await post_review(db, submission_id, datetime.now(timezone.utc))
    if note:
        await notify.publish([note])


async def sync_work_holidays_job(ctx: dict) -> int:
    async with _sessions(ctx)() as db:
        count = await sync_work_holidays(db, datetime.now(timezone.utc).date())
        await db.commit()
    log.info("work_holidays: %d ta auto sana yozildi", count)
    return count


async def embed_document_chunks_job(ctx: dict) -> int:
    async with _sessions(ctx)() as db:
        count = await embed_pending_chunks(db)
        await db.commit()
    if count:
        log.info("document_chunks: %d ta embedding yozildi", count)
    return count


async def day_report_job(ctx: dict, run_id: str, node_id: str) -> bool:
    async with _sessions(ctx)() as db:
        done = await write_day_report(db, uuid.UUID(run_id), node_id, datetime.now(timezone.utc))
    if done:
        await notify.publish([Note(uuid.UUID(run_id), "day_report", {"node_id": node_id})])
    return done


async def final_report_job(ctx: dict, run_id: str) -> bool:
    async with _sessions(ctx)() as db:
        done = await write_final_report(db, uuid.UUID(run_id), datetime.now(timezone.utc))
    if done:
        await notify.publish([Note(uuid.UUID(run_id), "final_report", {})])
    return done
