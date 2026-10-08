"""
Suhbat bosqichlaridan bildirishnoma (CONTRACT.md §25.5). Chaqiruvchi commit qiladi,
`interview_reminders` cron'i ham (`notifications/jobs.py`).
"""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import Company
from app.models.enums import ApplicationInterviewStatus
from app.models.talent import ApplicationInterview, Vacancy, VacancyApplication
from app.models.user import User
from app.notifications.kinds import Kind
from app.notifications.offers import company_staff
from app.notifications.service import notify
from app.talent.meetings import REMINDER_LEAD


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _student_link(vacancy: Vacancy) -> str:
    return f"/vacancies/{vacancy.id}"


def _company_link(vacancy: Vacancy) -> str:
    return f"/company/vacancies/{vacancy.id}"


async def proposed(db: AsyncSession, interview: ApplicationInterview, application: VacancyApplication,
                   vacancy: Vacancy, company_name: str, now: datetime) -> None:
    await notify(
        db, application.user_id, Kind.INTERVIEW_PROPOSED,
        {"vacancy_id": str(vacancy.id), "vacancy": vacancy.title, "company": company_name,
         "round": interview.round, "slots": list(interview.slots)},
        link=_student_link(vacancy), key=f"meeting:{interview.id}:proposed", at=now,
    )


async def cancelled(db: AsyncSession, interview: ApplicationInterview, application: VacancyApplication,
                    vacancy: Vacancy, company_name: str, now: datetime) -> None:
    await notify(
        db, application.user_id, Kind.INTERVIEW_CANCELLED,
        {"vacancy_id": str(vacancy.id), "vacancy": vacancy.title, "company": company_name,
         "starts_at": _iso(interview.starts_at)},
        link=_student_link(vacancy), key=f"meeting:{interview.id}:cancelled", at=now,
    )


async def _to_staff(db: AsyncSession, vacancy: Vacancy, kind: Kind, params: dict, key: str, now: datetime) -> None:
    for user_id in await company_staff(db, vacancy.company_id):
        await notify(db, user_id, kind, params, link=_company_link(vacancy), key=key, at=now)


async def confirmed(db: AsyncSession, interview: ApplicationInterview, vacancy: Vacancy,
                    candidate_name: str, now: datetime) -> None:
    await _to_staff(
        db, vacancy, Kind.INTERVIEW_CONFIRMED,
        {"vacancy_id": str(vacancy.id), "vacancy": vacancy.title, "candidate": candidate_name,
         "starts_at": _iso(interview.starts_at)},
        key=f"meeting:{interview.id}:confirmed", now=now,
    )


async def declined(db: AsyncSession, interview: ApplicationInterview, vacancy: Vacancy,
                   candidate_name: str, now: datetime, *, withdrawn: bool = False) -> None:
    await _to_staff(
        db, vacancy, Kind.INTERVIEW_DECLINED,
        {"vacancy_id": str(vacancy.id), "vacancy": vacancy.title, "candidate": candidate_name,
         "reason": interview.decline_reason, "withdrawn": withdrawn},
        key=f"meeting:{interview.id}:declined", now=now,
    )


async def interview_reminders(db: AsyncSession, now: datetime) -> int:
    """`confirmed` suhbatga ≤ 2 soat qoldi — talaba va kompaniya xodimlariga, bir marta (§25.5)."""
    rows = (await db.execute(
        select(ApplicationInterview, VacancyApplication, Vacancy, Company.name, User.full_name)
        .join(VacancyApplication, VacancyApplication.id == ApplicationInterview.application_id)
        .join(Vacancy, Vacancy.id == VacancyApplication.vacancy_id)
        .join(Company, Company.id == Vacancy.company_id)
        .join(User, User.id == VacancyApplication.user_id)
        .where(
            ApplicationInterview.status == ApplicationInterviewStatus.CONFIRMED,
            ApplicationInterview.reminded_at.is_(None),
            ApplicationInterview.starts_at > now,
            ApplicationInterview.starts_at <= now + REMINDER_LEAD,
        )
        .with_for_update(of=ApplicationInterview, skip_locked=True)
    )).all()
    for interview, application, vacancy, company_name, candidate_name in rows:
        params = {
            "vacancy_id": str(vacancy.id), "vacancy": vacancy.title, "company": company_name,
            "candidate": candidate_name, "starts_at": _iso(interview.starts_at),
            "format": interview.format.value, "place": interview.place,
        }
        key = f"meeting:{interview.id}:reminder"
        await notify(db, application.user_id, Kind.INTERVIEW_REMINDER, params,
                     link=_student_link(vacancy), key=key, at=now)
        await _to_staff(db, vacancy, Kind.INTERVIEW_REMINDER, params, key=key, now=now)
        interview.reminded_at = now
    return len(rows)
