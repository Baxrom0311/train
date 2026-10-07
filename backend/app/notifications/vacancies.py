"""Vakansiya arizalaridan bildirishnoma (CONTRACT.md §23.7). Chaqiruvchi commit qiladi."""
from datetime import datetime

from app.models.talent import Vacancy, VacancyApplication
from app.notifications.kinds import Kind
from app.notifications.offers import company_staff
from app.notifications.service import notify


async def application_received(db, application: VacancyApplication, vacancy: Vacancy, candidate_name: str, now: datetime) -> None:
    """Kompaniyaning barcha faol xodimlariga; qayta ariza (withdrawn → applied) qayta yubormaydi."""
    params = {"vacancy_id": str(vacancy.id), "vacancy": vacancy.title, "candidate": candidate_name}
    for user_id in await company_staff(db, vacancy.company_id):
        await notify(db, user_id, Kind.APPLICATION_RECEIVED, params,
                     link=f"/company/vacancies/{vacancy.id}", key=f"application:{application.id}", at=now)


async def application_rejected(db, application: VacancyApplication, vacancy: Vacancy, company_name: str, now: datetime) -> None:
    await notify(
        db, application.user_id, Kind.APPLICATION_REJECTED,
        {"vacancy_id": str(vacancy.id), "vacancy": vacancy.title, "company": company_name},
        link=f"/vacancies/{vacancy.id}", key=f"application:{application.id}:rejected", at=now,
    )
