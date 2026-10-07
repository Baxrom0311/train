"""Bildirishnoma turlari va kimga tegishliligi (CONTRACT.md §15.2)."""
from enum import Enum


class Kind(str, Enum):
    TASK_DELIVERED = "task_delivered"
    DEADLINE_SOON = "deadline_soon"
    MENTOR_REVIEW = "mentor_review"
    REPORT_READY = "report_ready"
    OFFER_RECEIVED = "offer_received"
    OFFER_RESPONDED = "offer_responded"


STUDENT_KINDS = (Kind.TASK_DELIVERED, Kind.DEADLINE_SOON, Kind.MENTOR_REVIEW, Kind.REPORT_READY, Kind.OFFER_RECEIVED)
COMPANY_KINDS = (Kind.OFFER_RESPONDED,)

# Qator yo'q bo'lsa emailga ketadiganlar; vazifa va izoh — saytda yetarli
EMAIL_DEFAULT = frozenset({Kind.DEADLINE_SOON, Kind.REPORT_READY, Kind.OFFER_RECEIVED, Kind.OFFER_RESPONDED})


def available_for(permissions: set[str]) -> list[Kind]:
    """Foydalanuvchi ruxsatlariga qarab tegishli turlar (§15.4) — rol nomi bo'yicha emas."""
    kinds: list[Kind] = []
    if "receive_offers" in permissions:
        kinds += STUDENT_KINDS
    if "view_candidates" in permissions:
        kinds += COMPANY_KINDS
    return kinds
