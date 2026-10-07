"""
Vakansiya va nomzod mosligi (CONTRACT.md §23.2) hamda mashq ssenariylari (§23.4).

`fit` — sof funksiya: profil (§10.1) va vakansiya talablaridan hisoblanadi,
DB'ga tegmaydi. Ssenariylar ro'yxati dvigatel interfeysi orqali faqat o'qiladi.
"""
from __future__ import annotations

import uuid
from collections import Counter
from dataclasses import dataclass
from statistics import fmean

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ScenarioVersionStatus
from app.models.scenario import Scenario, ScenarioVersion
from app.models.talent import Vacancy
from app.scenario.engine import definition_for
from app.talent.profile import Profile

MATCH_MIN_FIT = 50.0
MAX_MATCHES = 50
MAX_PRACTICE = 5


@dataclass(frozen=True)
class Gap:
    competency: str
    required: int
    actual: float | None


@dataclass(frozen=True)
class Fit:
    fit: float
    meets: bool
    gaps: list[Gap]
    sector_match: bool

    def sort_key(self, overall: float | None) -> tuple:
        return (self.meets, self.fit, self.sector_match, overall if overall is not None else -1)


def fit(profile: Profile, vacancy: Vacancy) -> Fit:
    """§23.2: talablar bo'yicha `min(1, ball / talab)` o'rtachasi; talab yo'q — umumiy ball."""
    requirements: dict[str, int] = vacancy.requirements or {}
    competencies = profile.competencies
    overall = profile.overall_score
    if requirements:
        ratios = []
        for key, required in requirements.items():
            actual = competencies.get(key)
            ratios.append(1.0 if required <= 0 else min(1.0, (actual or 0) / required))
        value = round(fmean(ratios) * 100, 1)
    else:
        value = overall if overall is not None else 0.0
    gaps = [
        Gap(key, required, competencies.get(key))
        for key, required in requirements.items()
        if (competencies.get(key) or 0) < required
    ]
    meets = not gaps and (vacancy.min_score is None or (overall is not None and overall >= vacancy.min_score))
    return Fit(fit=value, meets=meets, gaps=gaps, sector_match=vacancy.sector.value in profile.sectors)


@dataclass(frozen=True)
class ScenarioOption:
    scenario_id: uuid.UUID
    title: str
    sector: str
    company_name: str
    duration_days: int
    difficulty: str
    practices: dict[str, int]


async def published_scenarios(db: AsyncSession) -> dict[uuid.UUID, ScenarioOption]:
    """Faol, nashr qilingan ssenariylar va har kompetensiya necha marta baholanishi (§17.1 kabi)."""
    rows = (await db.execute(
        select(Scenario, ScenarioVersion)
        .join(ScenarioVersion, ScenarioVersion.scenario_id == Scenario.id)
        .where(Scenario.is_active.is_(True), ScenarioVersion.status == ScenarioVersionStatus.PUBLISHED)
    )).all()
    out = {}
    for scenario, version in rows:
        practices: Counter[str] = Counter()
        for node in definition_for(version).nodes:
            if node.is_graded:
                practices.update(c.value for c in node.competencies)
        out[scenario.id] = ScenarioOption(
            scenario_id=scenario.id, title=scenario.title, sector=scenario.sector.value,
            company_name=scenario.company_name, duration_days=scenario.duration_days,
            difficulty=scenario.difficulty, practices=dict(practices),
        )
    return out


def practice(
    vacancy: Vacancy, gaps: list[Gap], scenarios: dict[uuid.UUID, ScenarioOption], completed: set[uuid.UUID],
) -> list[tuple[ScenarioOption, bool, dict[str, int]]]:
    """
    §23.4: avval kompaniya ko'rsatganlari (tugatilgan bo'lsa ham, belgi bilan),
    so'ng yetishmayotgan kompetensiyalarni mashq qildiradigan, tugatilmaganlari.
    Natija: (ssenariy, tugatilganmi, shu vakansiya uchun mashq qilinadigan kompetensiyalar).
    """
    wanted = [g.competency for g in gaps] or list((vacancy.requirements or {}).keys())

    def relevant(option: ScenarioOption) -> dict[str, int]:
        return {k: option.practices[k] for k in wanted if option.practices.get(k)}

    out: list[tuple[ScenarioOption, bool, dict[str, int]]] = []
    for raw in vacancy.scenario_ids or []:
        option = scenarios.get(uuid.UUID(raw))
        if option:
            out.append((option, option.scenario_id in completed, relevant(option)))

    if gaps:
        chosen = {o.scenario_id for o, _, _ in out}
        extra = [
            (o, relevant(o)) for o in scenarios.values()
            if o.scenario_id not in chosen and o.scenario_id not in completed and relevant(o)
        ]
        # ko'proq mashq — oldinda, keyin vakansiya sohasi, keyin nom
        extra.sort(key=lambda x: (-sum(x[1].values()), x[0].sector != vacancy.sector.value, x[0].title))
        out += [(o, False, r) for o, r in extra]
    return out[:MAX_PRACTICE]
