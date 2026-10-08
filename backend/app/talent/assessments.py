"""
Sinov topshirig'i qoidalari (CONTRACT.md §26.2): holat Run'dan hisoblanadi,
natija faqat kompaniyaga, ariza yopilganda kutayotgan topshiriq bekor bo'ladi.

Chaqiruvchi ariza qatorini avval qulflaydi va commit qiladi.
"""
import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AssessmentStatus, RunStatus, ScenarioVersionStatus
from app.models.scenario import Run, Scenario, ScenarioVersion
from app.models.talent import ApplicationAssessment

MIN_DAYS, MAX_DAYS, DEFAULT_DAYS = 1, 14, 5
OPEN_RUN = (RunStatus.SCHEDULED, RunStatus.ACTIVE)


@dataclass(frozen=True)
class Item:
    """Topshiriq + ssenariy + (boshlangan bo'lsa) Run — chiqish uchun hammasi bir joyda."""
    assessment: ApplicationAssessment
    scenario: Scenario
    run: Run | None


def state(item: Item, now: datetime) -> str:
    a, run = item.assessment, item.run
    if a.status == AssessmentStatus.CANCELLED:
        return "cancelled"
    if a.status == AssessmentStatus.ASSIGNED:
        return "overdue" if now > a.start_by else "assigned"
    if run is None:                       # Run o'chirilgan (SET NULL) — natija yo'q
        return "abandoned"
    if run.status in OPEN_RUN:
        return "in_progress"
    if run.status == RunStatus.ABANDONED:
        return "abandoned"
    if run.final_report is None:
        return "evaluating"
    return "completed" if run.status == RunStatus.COMPLETED else "incomplete"


def result(item: Item) -> dict | None:
    """Yakuniy hisobotdan kompaniyaga ko'rinadigan qism (§26.2)."""
    report = item.run.final_report if item.run else None
    if not report:
        return None
    summary = report.get("summary") or {}
    return {
        "overall_score": report.get("overall_score"),
        "on_time_rate": report.get("on_time_rate"),
        "competency_scores": item.run.competency_scores or {},
        "summary": summary.get("summary"),
        "strengths": list(summary.get("strengths") or []),
        "improvements": list(summary.get("improvements") or []),
    }


async def items(db: AsyncSession, application_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[Item]]:
    """Arizalar bo'yicha topshiriqlar, yangilari tepada."""
    out: dict[uuid.UUID, list[Item]] = {i: [] for i in application_ids}
    if not application_ids:
        return out
    rows = (await db.execute(
        select(ApplicationAssessment, Scenario, Run)
        .join(Scenario, Scenario.id == ApplicationAssessment.scenario_id)
        .outerjoin(Run, Run.id == ApplicationAssessment.run_id)
        .where(ApplicationAssessment.application_id.in_(application_ids))
        .order_by(ApplicationAssessment.created_at.desc())
    )).all()
    for a, scenario, run in rows:
        out[a.application_id].append(Item(a, scenario, run))
    return out


async def item(db: AsyncSession, assessment: ApplicationAssessment) -> Item:
    run = await db.get(Run, assessment.run_id) if assessment.run_id else None
    return Item(assessment, await db.get(Scenario, assessment.scenario_id), run)


async def unfinished(db: AsyncSession, application_id: uuid.UUID) -> bool:
    """Kutayotgan yoki Run'i hali ochiq topshiriq bormi — yangisi yuborilmaydi (§26.2)."""
    row = (await db.execute(
        select(ApplicationAssessment.id)
        .outerjoin(Run, Run.id == ApplicationAssessment.run_id)
        .where(
            ApplicationAssessment.application_id == application_id,
            (ApplicationAssessment.status == AssessmentStatus.ASSIGNED)
            | ((ApplicationAssessment.status == AssessmentStatus.STARTED) & Run.status.in_(OPEN_RUN)),
        )
        .limit(1)
    )).first()
    return row is not None


async def company_version(
    db: AsyncSession, company_id: uuid.UUID, scenario_id: uuid.UUID,
) -> tuple[Scenario, ScenarioVersion] | None:
    """Kompaniyaning faol ssenariysi va uning nashr qilingan versiyasi; boshqasi — None."""
    row = (await db.execute(
        select(Scenario, ScenarioVersion)
        .join(ScenarioVersion, ScenarioVersion.scenario_id == Scenario.id)
        .where(
            Scenario.id == scenario_id,
            Scenario.owner_company_id == company_id,
            Scenario.is_active.is_(True),
            ScenarioVersion.status == ScenarioVersionStatus.PUBLISHED,
        )
    )).first()
    return (row[0], row[1]) if row else None


async def cancel_assigned(db: AsyncSession, application_id: uuid.UUID, now: datetime) -> None:
    """Ariza taklif/rad/qaytarib olish bilan yopildi — boshlanmagan topshiriq bekor (§26.2)."""
    rows = (await db.execute(
        select(ApplicationAssessment).where(
            ApplicationAssessment.application_id == application_id,
            ApplicationAssessment.status == AssessmentStatus.ASSIGNED,
        ).with_for_update()
    )).scalars().all()
    for a in rows:
        a.status = AssessmentStatus.CANCELLED
        a.updated_at = now
