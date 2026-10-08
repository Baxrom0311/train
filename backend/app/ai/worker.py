"""
arq background worker: AI eval retry + ssenariy dvigateli job'lari (§9.8).
Submission DB'dan olinadi, AI zanjiri qayta ishga tushiriladi.
3 marta muvaffaqiyatsiz bo'lsa — 'failed_permanent'.

Ishga tushirish (deploy/da): `arq app.ai.worker.WorkerSettings`
"""

import logging
from datetime import datetime, timezone

import httpx
from arq import Retry, cron, func
from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select

from app.config import settings
from app.models.simulation import Submission, SimulationTask, Simulation
from app.models.enums import AIEvalStatus
from app.ai.guardrail import validate_submission_content
from app.ai.router import run_ai_chain, _pick_persona, _build_user_prompt
from app.interview.jobs import MAX_TRIES as INTERVIEW_TRIES, REPORT_JOB as INTERVIEW_REPORT_JOB
from app.interview.jobs import interview_report_job, requeue_stale_interviews
from app.notifications.jobs import (
    deadline_reminders_job, interview_reminders_job, send_notification_emails_job, send_push_notifications_job,
)
from app.scenario.jobs import (
    DAY_REPORT_JOB,
    EVAL_JOB,
    FINAL_REPORT_JOB,
    day_report_job,
    final_report_job,
    deliver_due_events,
    embed_document_chunks_job,
    evaluate_run_submission_job,
    sync_work_holidays_job,
)

log = logging.getLogger(__name__)

MAX_ATTEMPTS = 3


def _make_session() -> async_sessionmaker:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def retry_ai_eval(ctx: dict, submission_id: str) -> None:
    """
    arq job — submission'ni DB'dan olib, AI zanjirini qayta ishga tushiradi.
    ctx['job_try'] — arq o'zi avtomatik hisoblaydi (har `Retry` qayta
    urinishda +1), shuning uchun alohida counter saqlash shart emas.

    Logika:
    - DB'dan Submission olinadi (+ sektor/ko'nikmalar uchun Task/Simulation)
    - Guardrail: agar muvaffaqiyatsiz — failed_permanent
    - AI zanjiri ishga tushiriladi
    - Muvaffaqiyatli: completed + ball yoziladi
    - Muvaffaqiyatsiz: attempts hisoblanadi
      * attempts < MAX_ATTEMPTS → arq.Retry (exponential backoff)
      * attempts >= MAX_ATTEMPTS → 'failed_permanent'
    """
    SessionLocal = _make_session()

    async with SessionLocal() as db:
        result = await db.execute(
            select(Submission).where(Submission.id == submission_id)
        )
        submission: Submission | None = result.scalars().first()

        if submission is None:
            log.error("retry_ai_eval: submission topilmadi id=%s", submission_id)
            return

        is_valid = await validate_submission_content(submission.content)
        if not is_valid:
            submission.ai_eval_status = AIEvalStatus.FAILED_PERMANENT
            submission.ai_feedback = "Content failed guardrail validation (retry)."
            submission.evaluated_at = datetime.now(timezone.utc)
            await db.commit()
            return

        # Sektor va kutilayotgan ko'nikmalarni Task/Simulation orqali olish
        # (avvalgi versiyada bular hech qachon uzatilmagan edi — shuning
        # uchun qayta urinishda ham doim IT mentori tanlanardi).
        sector = None
        expected_skills: list = []
        task_result = await db.execute(
            select(SimulationTask).where(SimulationTask.id == submission.task_id)
        )
        task = task_result.scalars().first()
        if task is not None:
            expected_skills = task.expected_skills or []
            sim_result = await db.execute(
                select(Simulation).where(Simulation.id == task.simulation_id)
            )
            simulation = sim_result.scalars().first()
            if simulation is not None:
                sector = simulation.sector

        attempt = ctx.get("job_try", 1)

        async with httpx.AsyncClient() as client:
            ai_result = await run_ai_chain(
                client,
                _pick_persona(sector).system_prompt,
                _build_user_prompt(submission.content, expected_skills),
            )

        if ai_result is not None:
            score, feedback = ai_result
            submission.ai_score = round(score, 1)
            submission.ai_feedback = feedback
            submission.ai_eval_status = AIEvalStatus.COMPLETED
            submission.evaluated_at = datetime.now(timezone.utc)
            await db.commit()
            log.info("retry_ai_eval: muvaffaqiyatli id=%s score=%.1f", submission_id, score)
            return

        if attempt >= MAX_ATTEMPTS:
            submission.ai_eval_status = AIEvalStatus.FAILED_PERMANENT
            submission.ai_feedback = f"AI eval {MAX_ATTEMPTS} marta urinishdan keyin muvaffaqiyatsiz."
            submission.evaluated_at = datetime.now(timezone.utc)
            await db.commit()
            log.warning(
                "retry_ai_eval: failed_permanent id=%s attempt=%d",
                submission_id, attempt,
            )
            return

        submission.ai_eval_status = AIEvalStatus.QUEUED_RETRY
        await db.commit()
        log.info(
            "retry_ai_eval: qayta navbatga id=%s attempt=%d/%d",
            submission_id, attempt, MAX_ATTEMPTS,
        )
        # arq'ga haqiqiy qayta urinishni bildirish — oldingi versiyada
        # bu o'rniga hech narsa anglatmaydigan oddiy Exception
        # (_RetrySignal) ko'tarilardi, arq buni "job muvaffaqiyatsiz
        # tugadi" deb hisoblab qayta urinmasdi.
        raise Retry(defer=2 ** attempt)


async def startup(ctx: dict) -> None:  # noqa: ARG001
    pass


async def shutdown(ctx: dict) -> None:  # noqa: ARG001
    pass


HEALTH_CHECK_INTERVAL = 60   # soniya; kalit TTL'i shundan 1 soniya ko'p (arq)


class WorkerSettings:
    """`arq app.ai.worker.WorkerSettings` bilan ishga tushiriladi (deploy/)."""
    functions = [
        retry_ai_eval,
        func(evaluate_run_submission_job, name=EVAL_JOB, max_tries=MAX_ATTEMPTS),
        # natija saqlanmaydi — hisobot hali yozilmagan bo'lsa cron shu _job_id bilan qayta qo'ya oladi
        func(day_report_job, name=DAY_REPORT_JOB, keep_result=0, max_tries=1),
        func(final_report_job, name=FINAL_REPORT_JOB, keep_result=0, max_tries=1),
        # §24.4: AI ishlamasa o'zi qayta urinadi; natija saqlanmaydi — cron qayta qo'ya oladi
        func(interview_report_job, name=INTERVIEW_REPORT_JOB, keep_result=0, max_tries=INTERVIEW_TRIES),
    ]
    cron_jobs = [
        # §9.8: har daqiqa — yetkazish, dedlaynlar, Run yopilishi
        cron(deliver_due_events, second=0, unique=True, timeout=50),
        # §9.2: haftalik bayramlar (va worker ishga tushganda bir marta)
        cron(sync_work_holidays_job, weekday="mon", hour=3, minute=0, run_at_startup=True),
        # §9.4: yangi import qilingan hujjatlar uchun embedding (kalit bo'lmasa — no-op)
        cron(embed_document_chunks_job, minute=set(range(0, 60, 5)), second=30, unique=True),
        # §15: dedlayn eslatmasi va email bildirishnomalar (SMTP sozlanmagan bo'lsa — no-op)
        cron(deadline_reminders_job, second=10, unique=True, timeout=50),
        cron(send_notification_emails_job, second=20, unique=True, timeout=50),
        # §22.2: push — yetkazish (0) va eslatmadan (10) keyin; VAPID bo'lmasa no-op
        cron(send_push_notifications_job, second=15, unique=True, timeout=50),
        # §24.4: navbatga tushmay qolgan suhbat baholari
        cron(requeue_stale_interviews, minute=set(range(2, 60, 5)), second=40, unique=True),
        # §25.5: arizachi bilan suhbatga ≤ 2 soat qoldi
        cron(interview_reminders_job, minute=set(range(0, 60, 5)), second=5, unique=True, timeout=50),
    ]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    # §18.1: `/api/v1/health` shu kalitni tekshiradi — worker o'lsa ~1 daqiqada ko'rinadi
    health_check_interval = HEALTH_CHECK_INTERVAL
    on_startup = startup
    on_shutdown = shutdown
    max_tries = MAX_ATTEMPTS
