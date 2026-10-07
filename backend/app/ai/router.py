"""
Cloud AI zanjiri: DeepSeek → Gemini → OpenAI → arq retry queue.
Haqiqiy HTTP chaqiruvlar httpx orqali. API key yo'q bo'lsa — keyingisiga o'tadi.
"""

import os
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.simulation import Submission
from app.ai.guardrail import validate_submission_content
from app.ai.personas import IT_MENTOR, FINANCE_MENTOR

log = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Yordamchi: persona tanlash
# ──────────────────────────────────────────────

def _pick_persona(sector: str | None):
    if sector and sector.upper() in ("BANK", "BANKING", "FINANCE"):
        return FINANCE_MENTOR
    return IT_MENTOR


def _build_user_prompt(content: str, expected_skills: list) -> str:
    skills_str = ", ".join(expected_skills) if expected_skills else "general skills"
    return (
        f"Please evaluate this student submission for skills: {skills_str}.\n\n"
        f"SUBMISSION:\n{content}\n\n"
        "Return a JSON object with two keys:\n"
        '  "score": float from 0 to 100\n'
        '  "feedback": string (2-3 sentences of constructive feedback)\n'
        "Return ONLY valid JSON, nothing else."
    )


# ──────────────────────────────────────────────
# Provider funksiyalari
# ──────────────────────────────────────────────

async def _call_deepseek(
    client: httpx.AsyncClient,
    system_prompt: str,
    user_prompt: str,
) -> tuple[float, str] | None:
    """
    DeepSeek Chat Completion API.
    Hujjat: https://platform.deepseek.com/api-docs/
    """
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not api_key:
        return None

    try:
        resp = await client.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 512,
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        import json as _json
        text = resp.json()["choices"][0]["message"]["content"]
        parsed = _json.loads(text)
        return float(parsed["score"]), str(parsed["feedback"])
    except Exception as exc:
        log.warning("DeepSeek chaqiruvi muvaffaqiyatsiz: %s", exc)
        return None


async def _call_gemini(
    client: httpx.AsyncClient,
    system_prompt: str,
    user_prompt: str,
) -> tuple[float, str] | None:
    """
    Google Gemini generateContent REST API.
    """
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return None

    try:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-1.5-flash:generateContent?key={api_key}"
        )
        body = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_prompt}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 512},
        }
        resp = await client.post(url, json=body, timeout=30.0)
        resp.raise_for_status()
        import json as _json
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        parsed = _json.loads(text)
        return float(parsed["score"]), str(parsed["feedback"])
    except Exception as exc:
        log.warning("Gemini chaqiruvi muvaffaqiyatsiz: %s", exc)
        return None


async def _call_openai(
    client: httpx.AsyncClient,
    system_prompt: str,
    user_prompt: str,
) -> tuple[float, str] | None:
    """
    OpenAI Chat Completion API.
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return None

    try:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 512,
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        import json as _json
        text = resp.json()["choices"][0]["message"]["content"]
        parsed = _json.loads(text)
        return float(parsed["score"]), str(parsed["feedback"])
    except Exception as exc:
        log.warning("OpenAI chaqiruvi muvaffaqiyatsiz: %s", exc)
        return None


# ──────────────────────────────────────────────
# Zanjir: DeepSeek → Gemini → OpenAI
# ──────────────────────────────────────────────

async def run_ai_chain(
    client: httpx.AsyncClient,
    system_prompt: str,
    user_prompt: str,
) -> tuple[float, str] | None:
    """
    Provayderlarni ketma-ket sinab ko'radi.
    Birinchi muvaffaqiyatli natijani qaytaradi.
    Hammasi muvaffaqiyatsiz bo'lsa — None.
    """
    result = await _call_deepseek(client, system_prompt, user_prompt)
    if result is not None:
        return result

    result = await _call_gemini(client, system_prompt, user_prompt)
    if result is not None:
        return result

    result = await _call_openai(client, system_prompt, user_prompt)
    return result  # None yoki (score, feedback)


# ──────────────────────────────────────────────
# Asosiy baholash funksiyasi
# ──────────────────────────────────────────────

async def evaluate_submission(
    submission: Submission,
    db: AsyncSession,
    redis=None,           # arq pool yoki None
    sector: str | None = None,
    expected_skills: list | None = None,
) -> None:
    """
    1. Guardrail tekshiruvi
    2. DeepSeek → Gemini → OpenAI zanjiri
    3. Hammasi muvaffaqiyatsiz bo'lsa: arq navbatiga qo'yadi
    """
    # — Guardrail —
    is_valid = await validate_submission_content(submission.content)
    if not is_valid:
        submission.ai_eval_status = "failed_permanent"
        submission.ai_feedback = "Content failed guardrail validation."
        submission.evaluated_at = datetime.now(timezone.utc)
        await db.commit()
        return

    # — AI zanjiri —
    persona = _pick_persona(sector)
    user_prompt = _build_user_prompt(
        submission.content,
        expected_skills or [],
    )

    async with httpx.AsyncClient() as client:
        result = await run_ai_chain(client, persona.system_prompt, user_prompt)

    if result is not None:
        score, feedback = result
        submission.ai_score = round(score, 1)
        submission.ai_feedback = feedback
        submission.ai_eval_status = "completed"
        submission.evaluated_at = datetime.now(timezone.utc)
        await db.commit()
        return

    # — Hamma provider muvaffaqiyatsiz: retry navbatiga —
    submission.ai_eval_status = "queued_retry"
    await db.commit()

    if redis is not None:
        try:
            import arq
            await redis.enqueue_job(
                "retry_ai_eval",
                str(submission.id),
            )
        except Exception as exc:
            log.error("arq navbatga qo'yish xatosi: %s", exc)
