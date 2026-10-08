"""
Ishga olish voronkasi (CONTRACT.md §27): ariza → sinov → suhbat → taklif → qabul.

Sof funksiyalar: kirish — kompaniya kogortasidagi arizalar va ularning
sinovlari, suhbatlari, takliflari (`Track`); DB va ruxsat tekshiruvi API
qatlamida. Yangi jadval yo'q — hammasi mavjud yozuvlardan hisoblanadi.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from statistics import median
from typing import Iterable

from app.models.enums import (
    ApplicationInterviewOutcome, ApplicationInterviewStatus, ApplicationStatus, AssessmentStatus, OfferResponse,
)
from app.models.talent import ApplicationInterview, TalentOffer, Vacancy, VacancyApplication
from app.talent import assessments
from app.talent.report import PENDING, percent, write_csv

STAGES = ("applied", "assessment", "interview", "offer", "hired")
DROPOFF_STAGES = STAGES[:3]           # rad etish/qaytarib olish taklifdan keyin bo'lmaydi (§25.2)
STALE_AFTER = timedelta(days=7)
FINISHED = ("completed", "incomplete")  # §26.2 — yakuniy hisobot yozilgan
HELD = (ApplicationInterviewOutcome.PASSED, ApplicationInterviewOutcome.FAILED)


@dataclass(frozen=True)
class Track:
    """Bitta arizaning butun yo'li; ro'yxatlar yangilari tepada."""
    application: VacancyApplication
    vacancy: Vacancy
    assessments: list[assessments.Item] = field(default_factory=list)
    interviews: list[ApplicationInterview] = field(default_factory=list)
    offers: list[TalentOffer] = field(default_factory=list)

    @property
    def accepted_offer(self) -> TalentOffer | None:
        return next((o for o in self.offers if o.response == OfferResponse.ACCEPTED), None)

    def reached(self) -> dict[str, bool]:
        """Ariza qaysi bosqichlarga o'tkazilgan (§27.1) — tartib erkin, bosqich ixtiyoriy."""
        return {
            "applied": True,
            "assessment": bool(self.assessments),
            "interview": bool(self.interviews),
            "offer": bool(self.offers),
            "hired": self.accepted_offer is not None,
        }

    def furthest(self) -> str:
        reached = self.reached()
        return next(s for s in reversed(STAGES) if reached[s])

    def first_action_at(self) -> datetime | None:
        """Kompaniyaning birinchi ijobiy qadami; rad etish qadam emas (§27.2)."""
        times = [
            *(i.assessment.created_at for i in self.assessments),
            *(i.created_at for i in self.interviews),
            *(o.created_at for o in self.offers),
        ]
        return min(times, default=None)

    def outcome(self) -> str:
        if self.accepted_offer is not None:
            return "hired"
        status = self.application.status
        if status == ApplicationStatus.WITHDRAWN:
            return "withdrawn"
        if status == ApplicationStatus.REJECTED:
            return "rejected"
        if self.offers:
            return "offer_pending" if self.offers[0].status in PENDING else "offer_declined"
        return "in_progress" if self.first_action_at() is not None else "waiting"


def _hours(start: datetime, end: datetime) -> float:
    return (end - start).total_seconds() / 3600


def _median(values: Iterable[float]) -> float | None:
    values = list(values)
    return round(median(values), 1) if values else None


def stages(tracks: list[Track]) -> list[dict]:
    """`rate` — arizalarga nisbatan, `step_rate` — oldingi bosqichga yetganlar ichida (§27.1)."""
    flags = [t.reached() for t in tracks]
    applied = len(flags)
    rows, prev = [], None
    for stage in STAGES:
        count = sum(f[stage] for f in flags)
        step = None
        if prev is not None:
            step = percent(sum(f[prev] and f[stage] for f in flags), sum(f[prev] for f in flags))
        rows.append({"stage": stage, "count": count, "rate": percent(count, applied), "step_rate": step})
        prev = stage
    return rows


def outcomes(tracks: list[Track], now: datetime) -> dict:
    counts = defaultdict(int)
    stale = 0
    for t in tracks:
        outcome = t.outcome()
        counts[outcome] += 1
        # qayta ariza (withdrawn → applied) updated_at'ni yangilaydi — kutish shundan boshlanadi
        if outcome == "waiting" and now - t.application.updated_at > STALE_AFTER:
            stale += 1
    keys = ("hired", "offer_pending", "offer_declined", "rejected", "withdrawn", "in_progress", "waiting")
    return {**{k: counts[k] for k in keys}, "stale": stale}


def dropoff(tracks: list[Track]) -> list[dict]:
    rows = {s: {"stage": s, "rejected": 0, "withdrawn": 0} for s in DROPOFF_STAGES}
    for t in tracks:
        outcome = t.outcome()
        if outcome in ("rejected", "withdrawn"):
            rows[t.furthest()][outcome] += 1
    return list(rows.values())


def assessment_stats(tracks: list[Track], now: datetime) -> dict:
    items = [i for t in tracks for i in t.assessments]
    started = sum(1 for i in items if i.assessment.status == AssessmentStatus.STARTED)
    finished = [i for i in items if assessments.state(i, now) in FINISHED]
    scores = [r["overall_score"] for r in map(assessments.result, finished) if r and r["overall_score"] is not None]
    return {
        "sent": len(items),
        "started": started,
        "completed": len(finished),
        "cancelled": sum(1 for i in items if i.assessment.status == AssessmentStatus.CANCELLED),
        "completion_rate": percent(len(finished), started),
        "avg_score": round(sum(scores) / len(scores), 1) if scores else None,
    }


def interview_stats(tracks: list[Track]) -> dict:
    items = [i for t in tracks for i in t.interviews]
    done = [i for i in items if i.status == ApplicationInterviewStatus.COMPLETED]
    held = sum(1 for i in done if i.outcome in HELD)
    passed = sum(1 for i in done if i.outcome == ApplicationInterviewOutcome.PASSED)
    no_show = sum(1 for i in done if i.outcome == ApplicationInterviewOutcome.NO_SHOW)
    return {
        "proposed": len(items),
        "confirmed": sum(1 for i in items if i.confirmed_at is not None),
        "declined": sum(1 for i in items if i.status == ApplicationInterviewStatus.DECLINED),
        "held": held,
        "passed": passed,
        "failed": held - passed,
        "no_show": no_show,
        "pass_rate": percent(passed, held),
        "show_rate": percent(held, held + no_show),
    }


def timing(tracks: list[Track]) -> dict:
    first, offer, hire = [], [], []
    for t in tracks:
        applied_at = t.application.created_at
        if (at := t.first_action_at()) is not None:
            first.append(_hours(applied_at, at))
        if t.offers:
            offer.append(_hours(applied_at, min(o.created_at for o in t.offers)) / 24)
        if (accepted := t.accepted_offer) is not None and accepted.responded_at is not None:
            hire.append(_hours(applied_at, accepted.responded_at) / 24)
    return {"first_action_hours": _median(first), "offer_days": _median(offer), "hire_days": _median(hire)}


def by_vacancy(tracks: list[Track]) -> list[dict]:
    groups: dict = defaultdict(list)
    for t in tracks:
        groups[t.vacancy.id].append(t)
    rows = []
    for items in groups.values():
        vacancy = items[0].vacancy
        counts = {row["stage"]: row["count"] for row in stages(items)}
        rows.append({
            "vacancy_id": vacancy.id, "title": vacancy.title, "status": vacancy.status.value,
            **counts, "hire_rate": percent(counts["hired"], counts["applied"]),
        })
    return sorted(rows, key=lambda r: (-r["applied"], r["title"].casefold()))


# ---------------------------------------------------------------------------
# CSV (§27.3)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CsvRow:
    """Qaytarib olingan arizalar bu yerga tushmaydi; email faqat taklif qabul qilinganda (§10.2)."""
    track: Track
    candidate_name: str
    candidate_email: str | None


def _last_score(track: Track, now: datetime) -> float | None:
    for item in track.assessments:                # yangilari tepada
        if assessments.state(item, now) in FINISHED and (r := assessments.result(item)):
            return r["overall_score"]
    return None


def _offer_status(track: Track) -> str | None:
    if not track.offers:
        return None
    latest = track.offers[0]
    return latest.response.value if latest.response else latest.status.value


def applications_csv(rows: list[CsvRow], now: datetime) -> str:
    return write_csv(
        ["applied_at", "vacancy", "candidate_name", "status", "furthest_stage", "assessment_score",
         "interviews_held", "offer_status", "first_action_at", "hired_at", "candidate_email"],
        (
            [
                r.track.application.created_at, r.track.vacancy.title, r.candidate_name,
                r.track.application.status.value, r.track.furthest(), _last_score(r.track, now),
                sum(1 for i in r.track.interviews if i.outcome in HELD), _offer_status(r.track),
                r.track.first_action_at(),
                r.track.accepted_offer.responded_at if r.track.accepted_offer else None,
                r.candidate_email,
            ]
            for r in rows
        ),
    )
