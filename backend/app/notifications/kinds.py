"""Bildirishnoma turlari va kimga tegishliligi (CONTRACT.md §15.2)."""
from enum import Enum


class Kind(str, Enum):
    TASK_DELIVERED = "task_delivered"
    DEADLINE_SOON = "deadline_soon"
    MENTOR_REVIEW = "mentor_review"
    REPORT_READY = "report_ready"
    OFFER_RECEIVED = "offer_received"
    OFFER_RESPONDED = "offer_responded"
    APPLICATION_RECEIVED = "application_received"    # §23.7
    APPLICATION_REJECTED = "application_rejected"
    INTERVIEW_PROPOSED = "interview_proposed"        # §25.5
    INTERVIEW_CANCELLED = "interview_cancelled"
    INTERVIEW_CONFIRMED = "interview_confirmed"
    INTERVIEW_DECLINED = "interview_declined"
    INTERVIEW_REMINDER = "interview_reminder"
    ASSESSMENT_ASSIGNED = "assessment_assigned"      # §26.5
    ASSESSMENT_COMPLETED = "assessment_completed"


STUDENT_KINDS = (
    Kind.TASK_DELIVERED, Kind.DEADLINE_SOON, Kind.MENTOR_REVIEW, Kind.REPORT_READY, Kind.OFFER_RECEIVED,
    Kind.APPLICATION_REJECTED, Kind.INTERVIEW_PROPOSED, Kind.INTERVIEW_CANCELLED, Kind.INTERVIEW_REMINDER,
    Kind.ASSESSMENT_ASSIGNED,
)
COMPANY_KINDS = (Kind.OFFER_RESPONDED,)
VACANCY_KINDS = (
    Kind.APPLICATION_RECEIVED, Kind.INTERVIEW_CONFIRMED, Kind.INTERVIEW_DECLINED, Kind.INTERVIEW_REMINDER,
    Kind.ASSESSMENT_COMPLETED,
)

# Qator yo'q bo'lsa emailga ketadiganlar; vazifa va izoh — saytda yetarli
EMAIL_DEFAULT = frozenset({
    Kind.DEADLINE_SOON, Kind.REPORT_READY, Kind.OFFER_RECEIVED, Kind.OFFER_RESPONDED, Kind.APPLICATION_RECEIVED,
    Kind.INTERVIEW_PROPOSED, Kind.INTERVIEW_CANCELLED, Kind.INTERVIEW_CONFIRMED, Kind.INTERVIEW_DECLINED,
    Kind.INTERVIEW_REMINDER, Kind.ASSESSMENT_ASSIGNED, Kind.ASSESSMENT_COMPLETED,
})


def available_for(permissions: set[str]) -> list[Kind]:
    """Foydalanuvchi ruxsatlariga qarab tegishli turlar (§15.4) — rol nomi bo'yicha emas."""
    kinds: list[Kind] = []
    if "receive_offers" in permissions:
        kinds += STUDENT_KINDS
    if "view_candidates" in permissions:
        kinds += COMPANY_KINDS
    if "manage_vacancies" in permissions:
        kinds += VACANCY_KINDS
    return list(dict.fromkeys(kinds))     # `interview_reminder` ikkala tomonda
