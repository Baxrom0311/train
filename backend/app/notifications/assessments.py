"""Sinov topshirig'idan bildirishnoma (CONTRACT.md §26.5). Chaqiruvchi commit qiladi."""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scenario import Run, Scenario
from app.models.talent import ApplicationAssessment, Vacancy, VacancyApplication
from app.models.user import User
from app.notifications.kinds import Kind
from app.notifications.offers import company_staff
from app.notifications.service import notify


async def assessment_assigned(db: AsyncSession, assessment: ApplicationAssessment, application: VacancyApplication,
                              vacancy: Vacancy, company_name: str, scenario_title: str, now: datetime) -> None:
    await notify(
        db, application.user_id, Kind.ASSESSMENT_ASSIGNED,
        {"vacancy_id": str(vacancy.id), "vacancy": vacancy.title, "company": company_name,
         "scenario": scenario_title, "start_by": assessment.start_by.isoformat()},
        link=f"/vacancies/{vacancy.id}", key=f"assessment:{assessment.id}:assigned", at=now,
    )


async def assessment_finished(db: AsyncSession, run: Run, now: datetime) -> None:
    """Yakuniy hisobot yozildi (`write_final_report`) — Run sinov bo'lsa kompaniya xodimlariga."""
    row = (await db.execute(
        select(ApplicationAssessment, Vacancy, User.full_name, Scenario.title)
        .join(VacancyApplication, VacancyApplication.id == ApplicationAssessment.application_id)
        .join(Vacancy, Vacancy.id == VacancyApplication.vacancy_id)
        .join(User, User.id == VacancyApplication.user_id)
        .join(Scenario, Scenario.id == ApplicationAssessment.scenario_id)
        .where(ApplicationAssessment.run_id == run.id)
    )).first()
    if row is None:
        return
    assessment, vacancy, candidate, scenario = row
    report = run.final_report or {}
    params = {
        "vacancy_id": str(vacancy.id), "vacancy": vacancy.title, "candidate": candidate, "scenario": scenario,
        "score": report.get("overall_score"), "incomplete": bool(report.get("incomplete")),
    }
    for user_id in await company_staff(db, vacancy.company_id):
        await notify(db, user_id, Kind.ASSESSMENT_COMPLETED, params, link=f"/company/vacancies/{vacancy.id}",
                     key=f"assessment:{assessment.id}:completed", at=now)
