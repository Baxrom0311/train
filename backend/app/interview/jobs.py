"""
Suhbatni baholash navbati (CONTRACT.md §24.4).

`interview_report_job` — arq (`app/ai/worker.py`da ro'yxatda). AI ishlamasa
qayta urinadi, `MAX_TRIES`dan keyin — `failed` (talaba "qayta baholash" bosa
oladi). `requeue_stale_interviews` — cron: navbatga tushmay qolganlar uchun.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from arq import Retry
from sqlalchemy import select

from app.interview import flow
from app.models.enums import InterviewStatus
from app.models.interview import Interview

log = logging.getLogger(__name__)

REPORT_JOB = "interview_report_job"
MAX_TRIES = 3
STALE_EVALUATING = timedelta(minutes=10)


def job_id(interview_id) -> str:
    return f"interview:{interview_id}"


async def enqueue_report(arq_pool, interview_id) -> None:
    try:
        await arq_pool.enqueue_job(REPORT_JOB, str(interview_id), _job_id=job_id(interview_id))
    except Exception as exc:  # noqa: BLE001 — cron qayta navbatga qo'yadi
        log.error("suhbat baholash navbatga qo'yilmadi (%s): %s", interview_id, exc)


def _sessions(ctx: dict):
    if "session_factory" in ctx:
        return ctx["session_factory"]
    from app.database import AsyncSessionLocal
    return AsyncSessionLocal


async def interview_report_job(ctx: dict, interview_id: str) -> bool:
    job_try = ctx.get("job_try", 1)
    iid = uuid.UUID(interview_id)
    async with _sessions(ctx)() as db:
        done = await flow.evaluate(db, iid, datetime.now(timezone.utc))
    if done:
        return True
    if job_try < MAX_TRIES:
        raise Retry(defer=5 * 2 ** job_try)
    async with _sessions(ctx)() as db:
        await flow.mark_failed(db, iid)
    return False


async def requeue_stale_interviews(ctx: dict) -> int:
    cutoff = datetime.now(timezone.utc) - STALE_EVALUATING
    async with _sessions(ctx)() as db:
        ids = list((await db.execute(
            select(Interview.id).where(Interview.status == InterviewStatus.EVALUATING, Interview.finished_at < cutoff)
        )).scalars())
    for iid in ids:
        await enqueue_report(ctx["redis"], iid)
    return len(ids)
