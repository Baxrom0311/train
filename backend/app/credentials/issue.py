"""
Sertifikat berish (CONTRACT.md §13.1).

`issue_for_run` dvigatel yakuniy hisobotni yozgan tranzaksiya ichida
chaqiriladi va commit qilmaydi; `run_id` UNIQUE bo'lgani uchun qayta
chaqiruv ikkinchi sertifikat yaratmaydi.
"""
from __future__ import annotations

import re
import secrets

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.credential import Certificate
from app.models.enums import RunStatus
from app.models.scenario import Run, Scenario, ScenarioVersion
from app.models.user import User

ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"   # 0/O/1/I/L yo'q
PREFIX = "TJ"
_CODE = re.compile(rf"^{PREFIX}-[{ALPHABET}]{{4}}-[{ALPHABET}]{{4}}$")


def new_code() -> str:
    body = "".join(secrets.choice(ALPHABET) for _ in range(8))
    return f"{PREFIX}-{body[:4]}-{body[4:]}"


def normalize_code(raw: str) -> str | None:
    """`tj 4k7m 9qxr`, `TJ4K7M9QXR` → `TJ-4K7M-9QXR`; noto'g'ri shakl → None."""
    compact = re.sub(r"[\s-]", "", raw).upper()
    if not compact.startswith(PREFIX) or len(compact) != len(PREFIX) + 8:
        return None
    body = compact[len(PREFIX):]
    code = f"{PREFIX}-{body[:4]}-{body[4:]}"
    return code if _CODE.match(code) else None


def eligible(run: Run) -> bool:
    return run.status == RunStatus.COMPLETED and bool((run.final_report or {}).get("certificate"))


async def _unused_code(db: AsyncSession) -> str:
    for _ in range(5):
        code = new_code()
        if not await db.scalar(select(Certificate.id).where(Certificate.code == code)):
            return code
    raise RuntimeError("sertifikat kodi topilmadi")   # 31^8 ≈ 8.5·10^11 — amalda bo'lmaydi


async def issue_for_run(db: AsyncSession, run: Run) -> str | None:
    """Sertifikat suratini qo'shadi va kodini qaytaradi (commit — chaqiruvchida). Shart bajarilmasa — None."""
    if not eligible(run):
        return None
    scenario = (await db.execute(
        select(Scenario).join(ScenarioVersion, ScenarioVersion.scenario_id == Scenario.id)
        .where(ScenarioVersion.id == run.scenario_version_id)
    )).scalars().one()
    holder = await db.get(User, run.user_id)
    report = run.final_report or {}
    await db.execute(
        insert(Certificate).values(
            code=await _unused_code(db),
            run_id=run.id,
            user_id=run.user_id,
            holder_name=holder.full_name,
            scenario_title=scenario.title,
            company_name=scenario.company_name,
            sector=scenario.sector.value,
            difficulty=scenario.difficulty,
            duration_days=scenario.duration_days,
            completed_at=run.last_activity_at,
            overall_score=report.get("overall_score"),
            competency_scores=run.competency_scores or report.get("competency_scores") or {},
        ).on_conflict_do_nothing(index_elements=[Certificate.run_id])
    )
    return await db.scalar(select(Certificate.code).where(Certificate.run_id == run.id))
