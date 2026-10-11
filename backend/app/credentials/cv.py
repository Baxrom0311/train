"""
Talaba CV'si (CONTRACT.md §28.1).

CV §10.1 profilidan yig'iladi: qaysi Run'lar kirishi, umumiy ball va
kompetensiyalar — profilniki. Bu modul faqat "Amaliy tajriba" yozuvlarini
Run va ssenariy tafsilotlari (sanalar, vazifalar, sertifikat kodi) bilan
to'ldiradi. Yashirish faqat yozuvni varaqdan tushiradi, ballarga tegmaydi.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.credential import Certificate
from app.models.enums import RunEventStatus
from app.models.scenario import Run, Scenario, ScenarioVersion
from app.talent.profile import Profile

TOP_COMPETENCIES = 3
MAX_STRENGTHS = 3


@dataclass(frozen=True)
class Experience:
    run_id: uuid.UUID
    scenario_title: str
    company_name: str
    sector: str
    difficulty: str
    duration_days: int
    started_at: datetime
    completed_at: datetime
    overall_score: float | None
    on_time_rate: float | None
    tasks_submitted: int
    tasks_total: int
    top_competencies: dict[str, float]
    strengths: list[str]
    certificate_code: str | None
    hidden: bool


def task_counts(tasks: list[dict]) -> tuple[int, int]:
    """(topshirilgan, jami) — §9.6 `on_time_rate` bilan bir xil maxraj: muddati bor va yopilgan vazifalar."""
    submitted = sum(1 for t in tasks if t.get("status") == RunEventStatus.SUBMITTED.value)
    missed = sum(1 for t in tasks if t.get("status") == RunEventStatus.MISSED.value)
    return submitted, submitted + missed


def top_competencies(scores: dict[str, float], n: int = TOP_COMPETENCIES) -> dict[str, float]:
    """Eng kuchli `n` ta; teng ballda — nom bo'yicha (varaq har safar bir xil chiqsin)."""
    return dict(sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[:n])


async def experience(db: AsyncSession, profile: Profile | None, hidden: set[uuid.UUID]) -> list[Experience]:
    """Profil Run'lari (yangisi birinchi) — yashirilganlari ham, `hidden` belgisi bilan."""
    if profile is None or not profile.runs:
        return []
    rows = (await db.execute(
        select(Run, Scenario, Certificate.code)
        .join(ScenarioVersion, Run.scenario_version_id == ScenarioVersion.id)
        .join(Scenario, ScenarioVersion.scenario_id == Scenario.id)
        .outerjoin(Certificate, and_(Certificate.run_id == Run.id, Certificate.revoked_at.is_(None)))
        .where(Run.id.in_([r.run_id for r in profile.runs]))
    )).all()
    details = {run.id: (run, scenario, code) for run, scenario, code in rows}

    out = []
    for summary in profile.runs:
        run, scenario, code = details[summary.run_id]
        report = run.final_report or {}
        submitted, total = task_counts(report.get("tasks") or [])
        out.append(Experience(
            run_id=run.id,
            scenario_title=summary.scenario_title,
            company_name=summary.company_name,
            sector=summary.sector,
            difficulty=scenario.difficulty,
            duration_days=scenario.duration_days,
            started_at=run.start_at,
            completed_at=summary.completed_at,
            overall_score=summary.overall_score,
            on_time_rate=report.get("on_time_rate"),
            tasks_submitted=submitted,
            tasks_total=total,
            top_competencies=top_competencies(summary.competency_scores),
            strengths=summary.strengths[:MAX_STRENGTHS],
            certificate_code=code,
            hidden=run.id in hidden,
        ))
    return out


async def own_run_ids(db: AsyncSession, user_id: uuid.UUID, ids: list[uuid.UUID]) -> list[uuid.UUID]:
    """Faqat talabaning o'z Run'lari, kelgan tartibda va takrorsiz (§28.2)."""
    if not ids:
        return []
    mine = set((await db.execute(
        select(Run.id).where(Run.id.in_(ids), Run.user_id == user_id)
    )).scalars())
    return [i for i in dict.fromkeys(ids) if i in mine]
