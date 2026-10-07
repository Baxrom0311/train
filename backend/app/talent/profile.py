"""
Kandidat profili — tugallangan Run'lar natijasidan (CONTRACT.md §10.1).

Dvigatel jadvallarini faqat o'qiydi. Hisob Python'da: pilot hajmida
(yuzlab nomzod) bitta so'rov bilan barcha tugallangan Run'larni olib,
xotirada guruhlash SQL'dagi JSONB o'rtachalaridan soddaroq va aniqroq.
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from statistics import fmean

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import RunStatus
from app.models.scenario import Run, Scenario, ScenarioVersion

TOP_COMPETENCIES = 3


@dataclass(frozen=True)
class RunSummary:
    run_id: uuid.UUID
    scenario_id: uuid.UUID
    scenario_title: str
    company_name: str
    sector: str
    completed_at: datetime
    overall_score: float | None
    competency_scores: dict[str, float]
    strengths: list[str]


@dataclass
class Profile:
    user_id: uuid.UUID
    runs: list[RunSummary] = field(default_factory=list)

    @property
    def overall_score(self) -> float | None:
        scores = [r.overall_score for r in self.runs if r.overall_score is not None]
        return round(fmean(scores), 1) if scores else None

    @property
    def competencies(self) -> dict[str, float]:
        acc: dict[str, list[float]] = defaultdict(list)
        for r in self.runs:
            for key, value in r.competency_scores.items():
                acc[key].append(value)
        return {k: round(fmean(v), 1) for k, v in sorted(acc.items())}

    @property
    def top_competencies(self) -> dict[str, float]:
        best = sorted(self.competencies.items(), key=lambda kv: -kv[1])[:TOP_COMPETENCIES]
        return dict(best)

    @property
    def sectors(self) -> list[str]:
        return sorted({r.sector for r in self.runs})

    @property
    def last_completed_at(self) -> datetime | None:
        return max((r.completed_at for r in self.runs), default=None)


def _completed_runs(user_ids: Select | list[uuid.UUID]) -> Select:
    return (
        select(Run, Scenario)
        .join(ScenarioVersion, Run.scenario_version_id == ScenarioVersion.id)
        .join(Scenario, ScenarioVersion.scenario_id == Scenario.id)
        .where(
            Run.user_id.in_(user_ids),
            Run.status == RunStatus.COMPLETED,
            Run.final_report.is_not(None),
        )
    )


def _summary(run: Run, scenario: Scenario) -> RunSummary:
    report = run.final_report or {}
    ai = report.get("summary") or {}
    return RunSummary(
        run_id=run.id,
        scenario_id=scenario.id,
        scenario_title=scenario.title,
        company_name=scenario.company_name,
        sector=scenario.sector.value,
        completed_at=run.last_activity_at,
        overall_score=report.get("overall_score"),
        competency_scores=run.competency_scores or {},
        strengths=list(ai.get("strengths") or []),
    )


def _better(a: RunSummary, b: RunSummary) -> bool:
    """`a` `b`dan yaxshiroqmi: balli yuqori, teng bo'lsa — yangiroq."""
    return ((a.overall_score or -1), a.completed_at) > ((b.overall_score or -1), b.completed_at)


async def build_profiles(db: AsyncSession, user_ids: Select | list[uuid.UUID]) -> dict[uuid.UUID, Profile]:
    """Har foydalanuvchi uchun profil; tugallangan Run'i yo'qlar natijaga kirmaydi."""
    best: dict[tuple[uuid.UUID, uuid.UUID], RunSummary] = {}
    for run, scenario in (await db.execute(_completed_runs(user_ids))).all():
        summary = _summary(run, scenario)
        key = (run.user_id, scenario.id)
        if key not in best or _better(summary, best[key]):
            best[key] = summary

    profiles: dict[uuid.UUID, Profile] = {}
    for (user_id, _), summary in best.items():
        profiles.setdefault(user_id, Profile(user_id)).runs.append(summary)
    for p in profiles.values():
        p.runs.sort(key=lambda r: r.completed_at, reverse=True)
    return profiles
