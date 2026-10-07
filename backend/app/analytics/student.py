"""
Talaba analitikasi (CONTRACT.md §17): o'z tugallangan Run'lari bo'yicha o'sish.

Run va ssenariy jadvallarini faqat o'qiydi. Hisob sof funksiyalarda
(`build`), DB'dan o'qish — `load`da: pilot hajmida talabaning Run'lari
o'nlab, xotirada hisoblash soddaroq.
"""
from __future__ import annotations

import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from statistics import fmean

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.credential import Certificate
from app.models.enums import RunStatus, ScenarioVersionStatus
from app.models.scenario import Run, Scenario, ScenarioVersion
from app.scenario.engine import definition_for
from app.talent.profile import completed_runs

RECENT = 3          # `current` — oxirgi shuncha qiymat o'rtachasi
FOCUS = 2           # eng zaif kompetensiyalar soni
FLAT = 3.0          # ± shu ichida — `flat`
MAX_IMPROVEMENTS = 4
MAX_RECOMMENDATIONS = 3


@dataclass(frozen=True)
class Point:
    run_id: uuid.UUID
    scenario_id: uuid.UUID
    scenario_title: str
    sector: str
    completed_at: datetime
    overall_score: float | None
    on_time_rate: float | None
    competency_scores: dict[str, float]
    improvements: list[str]


@dataclass(frozen=True)
class Candidate:
    """Tavsiya uchun ssenariy: baholanadigan node'larda kompetensiyalar necha marta uchraydi."""
    scenario_id: uuid.UUID
    title: str
    sector: str
    company_name: str
    duration_days: int
    difficulty: str
    practices: dict[str, int]


@dataclass
class Analytics:
    summary: dict
    timeline: list[Point]
    competencies: list[dict]
    sectors: list[dict]
    focus: list[dict]
    improvements: list[str]
    recommendations: list[dict] = field(default_factory=list)


def _mean(values: list[float]) -> float | None:
    return round(fmean(values), 1) if values else None


def _competency(key: str, values: list[float]) -> dict:
    """`first` — boshlang'ich nuqta; `current` undan keyingi oxirgi RECENT ta qiymatdan (§17.1)."""
    if len(values) < 2:
        return {"key": key, "current": values[0], "first": values[0], "delta": None, "trend": "new", "values": values}
    current = fmean(values[1:][-RECENT:])
    delta = current - values[0]
    trend = "flat" if abs(delta) <= FLAT else ("up" if delta > 0 else "down")
    return {
        "key": key, "current": round(current, 1), "first": values[0], "delta": round(delta, 1),
        "trend": trend, "values": values,
    }


def build(points: list[Point], in_progress: int, certificates: int, candidates: list[Candidate]) -> Analytics:
    """`points` — eskidan yangiga."""
    scores = [p.overall_score for p in points if p.overall_score is not None]
    rates = [p.on_time_rate for p in points if p.on_time_rate is not None]

    series: dict[str, list[float]] = defaultdict(list)
    for p in points:
        for key, value in p.competency_scores.items():
            series[key].append(value)
    competencies = sorted(
        (_competency(key, values) for key, values in series.items()),
        key=lambda c: (-c["current"], c["key"]),
    )
    weakest = sorted(competencies, key=lambda c: (c["current"], c["key"]))[:FOCUS]
    focus = [{"key": c["key"], "current": c["current"], "trend": c["trend"]} for c in weakest]

    by_sector: dict[str, list[float | None]] = defaultdict(list)
    for p in points:
        by_sector[p.sector].append(p.overall_score)
    sectors = sorted(
        (
            {"sector": s, "runs": len(v), "avg_score": _mean([x for x in v if x is not None])}
            for s, v in by_sector.items()
        ),
        key=lambda s: (-s["runs"], s["sector"]),
    )

    done = {p.scenario_id for p in points}
    focus_keys = [f["key"] for f in focus]
    ranked = []
    for c in candidates:
        if c.scenario_id in done:
            continue
        hits = sum(c.practices.get(k, 0) for k in focus_keys)
        if hits:
            ranked.append((hits, c))
    ranked.sort(key=lambda hc: (-hc[0], hc[1].title))

    return Analytics(
        summary={
            "completed": len(points),
            "in_progress": in_progress,
            "avg_score": _mean(scores),
            "best_score": max(scores) if scores else None,
            "on_time_rate": _mean(rates),
            "certificates": certificates,
        },
        timeline=points,
        competencies=competencies,
        sectors=sectors,
        focus=focus,
        improvements=points[-1].improvements[:MAX_IMPROVEMENTS] if points else [],
        recommendations=[
            {
                "scenario_id": c.scenario_id, "title": c.title, "sector": c.sector, "company_name": c.company_name,
                "duration_days": c.duration_days, "difficulty": c.difficulty,
                "practices": {k: c.practices[k] for k in focus_keys if c.practices.get(k)},
            }
            for _, c in ranked[:MAX_RECOMMENDATIONS]
        ],
    )


def _point(run: Run, scenario: Scenario) -> Point:
    report = run.final_report or {}
    ai = report.get("summary") or {}
    return Point(
        run_id=run.id,
        scenario_id=scenario.id,
        scenario_title=scenario.title,
        sector=scenario.sector.value,
        completed_at=run.last_activity_at,
        overall_score=report.get("overall_score"),
        on_time_rate=report.get("on_time_rate"),
        competency_scores=run.competency_scores or {},
        improvements=[str(x) for x in ai.get("improvements") or []],
    )


async def _candidates(db: AsyncSession) -> list[Candidate]:
    rows = (await db.execute(
        select(Scenario, ScenarioVersion)
        .join(ScenarioVersion, ScenarioVersion.scenario_id == Scenario.id)
        .where(Scenario.is_active.is_(True), ScenarioVersion.status == ScenarioVersionStatus.PUBLISHED)
    )).all()
    out = []
    for scenario, version in rows:
        practices: Counter[str] = Counter()
        for node in definition_for(version).nodes:
            if node.is_graded:
                practices.update(c.value for c in node.competencies)
        out.append(Candidate(
            scenario_id=scenario.id, title=scenario.title, sector=scenario.sector.value,
            company_name=scenario.company_name, duration_days=scenario.duration_days,
            difficulty=scenario.difficulty, practices=dict(practices),
        ))
    return out


async def load(db: AsyncSession, user_id: uuid.UUID) -> Analytics:
    rows = (await db.execute(completed_runs([user_id]))).all()
    points = sorted((_point(run, scenario) for run, scenario in rows), key=lambda p: p.completed_at)
    in_progress = await db.scalar(
        select(func.count()).select_from(Run)
        .where(Run.user_id == user_id, Run.status.in_((RunStatus.SCHEDULED, RunStatus.ACTIVE)))
    ) or 0
    certificates = await db.scalar(
        select(func.count()).select_from(Certificate)
        .where(Certificate.user_id == user_id, Certificate.revoked_at.is_(None))
    ) or 0
    # Run bo'lmasa fokus ham yo'q — ssenariylarni o'qishga hojat yo'q
    candidates = await _candidates(db) if points else []
    return build(points, in_progress, certificates, candidates)
