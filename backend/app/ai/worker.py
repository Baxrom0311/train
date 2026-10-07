"""
arq background worker: AI eval retry.
Submission DB'dan olinadi, AI zanjiri qayta ishga tushiriladi.
3 marta muvaffaqiyatsiz bo'lsa — 'failed_permanent'.
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select

from app.config import settings
from app.models.simulation import Submission
from app.models.enums import AIEvalStatus
from app.ai.guardrail import validate_submission_content
from app.ai.router import run_ai_chain, _pick_persona, _build_user_prompt

log = logging.getLogger(__name__)

MAX_ATTEMPTS = 3


def _make_session() -> async_sessionmaker:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def retry_ai_eval(ctx: dict, submission_id: str) -> None:
    """
    arq job — submission'ni DB'dan olib, AI zanjirini qayta ishga tushiradi.
    ctx['redis'] arq pool.

    Logika:
    - DB'dan Submission olinadi
    - Guardrail: agar muvaffaqiyatsiz — failed_permanent
    - AI zanjiri ishga tushiriladi
    - Muvaffaqiyatli: completed + ball yoziladi
    - Muvaffaqiyatsiz: attempts hisoblanadi
      * attempts < MAX_ATTEMPTS → 'queued_retry' qolib, qayta navbatga
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

        # Guardrail tekshiruvi
        is_valid = await validate_submission_content(submission.content)
        if not is_valid:
            submission.ai_eval_status = AIEvalStatus.FAILED_PERMANENT
            submission.ai_feedback = "Content failed guardrail validation (retry)."
            submission.evaluated_at = datetime.now(timezone.utc)
            await db.commit()
            return

        # Urinishlar sonini kuzatish (ai_feedback orqali minimal metadata)
        # Asosiy mantiq: retry_count ai_feedback prefix sifatida saqlanadi
        # Yoki — model'ga retry_count ustun qo'shilmagan, shuning uchun
        # kontekst sifatida faqat MAX_ATTEMPTS ishlatamiz.
        # Haqiqiy count uchun arq job_id / tries ni ctx'dan olamiz.
        # arq ctx'da 'job_try' mavjud bo'lsa — undan foydalanamiz.
        attempt = ctx.get("job_try", 1)  # arq 1-dan boshlaydi

        # AI zanjiri
        async with httpx.AsyncClient() as client:
            ai_result = await run_ai_chain(
                client,
                _pick_persona(None).system_prompt,
                _build_user_prompt(submission.content, []),
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

        # Muvaffaqiyatsiz
        if attempt >= MAX_ATTEMPTS:
            submission.ai_eval_status = AIEvalStatus.FAILED_PERMANENT
            submission.ai_feedback = f"AI eval {MAX_ATTEMPTS} marta urinishdan keyin muvaffaqiyatsiz."
            submission.evaluated_at = datetime.now(timezone.utc)
            await db.commit()
            log.warning(
                "retry_ai_eval: failed_permanent id=%s attempt=%d",
                submission_id, attempt,
            )
        else:
            # arq avtomatik qayta urinadi (raises arq.Retry yoki re-enqueue)
            submission.ai_eval_status = AIEvalStatus.QUEUED_RETRY
            await db.commit()
            log.info(
                "retry_ai_eval: qayta navbatga id=%s attempt=%d/%d",
                submission_id, attempt, MAX_ATTEMPTS,
            )
            # arq'ga qayta urinishni bildirish
            raise _RetrySignal(f"Attempt {attempt} muvaffaqiyatsiz, qayta uriniladi")


class _RetrySignal(Exception):
    """arq Retry signali — worker qayta urinishi uchun."""


# arq WorkerSettings uchun eksport
async def startup(ctx: dict) -> None:  # noqa: ARG001
    pass


async def shutdown(ctx: dict) -> None:  # noqa: ARG001
    pass
