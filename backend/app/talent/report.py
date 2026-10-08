"""
Kompaniya hisoboti — nomzodlar bazasi va takliflar voronkasi (CONTRACT.md §20).

Sof funksiyalar: kirish — kompaniyaga ko'rinadigan profillar (§10.1) va
kompaniyaning o'z takliflari; DB va ruxsat tekshiruvi API qatlamida.
"""
from __future__ import annotations

import csv
import io
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from statistics import fmean, median
from typing import Iterable

from app.models.enums import Competency, OfferResponse, TalentOfferStatus
from app.models.talent import TalentOffer
from app.scenario.clock import TASHKENT
from app.talent.profile import Profile

# (yorliq, quyi chegara) — yuqoridan pastga; §20.2
SCORE_BANDS = (("85-100", 85), ("70-84", 70), ("50-69", 50), ("0-49", 0))
PENDING = (TalentOfferStatus.SENT, TalentOfferStatus.VIEWED)
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


@dataclass(frozen=True)
class OfferRow:
    """Taklif va nomzod ismi/emaili — email faqat accepted'da (§10.2)."""
    offer: TalentOffer
    candidate_name: str
    candidate_email: str | None


def percent(part: int, whole: int) -> float | None:
    return round(part * 100 / whole, 1) if whole else None


def _avg(values: Iterable[float]) -> float | None:
    values = list(values)
    return round(fmean(values), 1) if values else None


def pool_stats(profiles: list[Profile], since: datetime | None) -> dict:
    scored = [p.overall_score for p in profiles if p.overall_score is not None]
    bands = Counter()
    for score in scored:
        bands[next(label for label, low in SCORE_BANDS if score >= low)] += 1

    by_sector: dict[str, list[float | None]] = defaultdict(list)
    competencies: dict[str, list[float]] = defaultdict(list)
    for p in profiles:
        for sector in p.sectors:
            by_sector[sector].append(p.overall_score)
        for key, value in p.competencies.items():
            competencies[key].append(value)

    return {
        "candidates": len(profiles),
        "active_in_period": sum(
            1 for p in profiles if since is None or (p.last_completed_at and p.last_completed_at >= since)
        ),
        "avg_score": _avg(scored),
        "score_bands": [{"band": label, "candidates": bands[label]} for label, _ in reversed(SCORE_BANDS)],
        "sectors": sorted(
            (
                {"sector": s, "candidates": len(v), "avg_score": _avg(x for x in v if x is not None)}
                for s, v in by_sector.items()
            ),
            key=lambda row: (-row["candidates"], row["sector"]),
        ),
        "competencies": {k: _avg(competencies[k]) for k in (c.value for c in Competency) if k in competencies},
    }


def response_hours(offer: TalentOffer) -> float | None:
    if offer.responded_at is None or offer.created_at is None:
        return None
    return round((offer.responded_at - offer.created_at).total_seconds() / 3600, 1)


def offer_stats(offers: list[TalentOffer], now: datetime) -> dict:
    status = Counter(o.status for o in offers)
    response = Counter(o.response for o in offers if o.status == TalentOfferStatus.RESPONDED)
    sent = len(offers)
    responded = status[TalentOfferStatus.RESPONDED]
    hours = [h for h in map(response_hours, offers) if h is not None]
    return {
        "sent": sent,
        "viewed": status[TalentOfferStatus.VIEWED] + responded,
        "responded": responded,
        "accepted": response[OfferResponse.ACCEPTED],
        "declined": response[OfferResponse.DECLINED],
        "pending": sum(status[s] for s in PENDING),
        "overdue": sum(
            1 for o in offers if o.status in PENDING and o.respond_due_at is not None and o.respond_due_at < now
        ),
        "response_rate": percent(responded, sent),
        "acceptance_rate": percent(response[OfferResponse.ACCEPTED], responded),
        "median_response_hours": round(median(hours), 1) if hours else None,
    }


def by_position(offers: list[TalentOffer]) -> list[dict]:
    """Lavozim nomi katta-kichik harfga va chetdagi bo'sh joyga qaramay guruhlanadi."""
    groups: dict[str, list[TalentOffer]] = defaultdict(list)
    for o in offers:
        groups[" ".join(o.position_title.split()).casefold()].append(o)
    rows = []
    for items in groups.values():
        title = Counter(" ".join(o.position_title.split()) for o in items).most_common(1)[0][0]
        rows.append({
            "position_title": title,
            "sent": len(items),
            "accepted": sum(1 for o in items if o.response == OfferResponse.ACCEPTED),
            "declined": sum(1 for o in items if o.response == OfferResponse.DECLINED),
            "pending": sum(1 for o in items if o.status in PENDING),
        })
    return sorted(rows, key=lambda r: (-r["sent"], r["position_title"].casefold()))


def _month(dt: datetime) -> tuple[int, int]:
    local = dt.astimezone(TASHKENT)
    return local.year, local.month


def by_month(offers: list[TalentOffer], since: datetime | None, now: datetime) -> list[dict]:
    """Toshkent vaqti bo'yicha oylar, eskidan yangiga; oraliqdagi bo'sh oylar ham (§20.2)."""
    if not offers:
        return []
    counts: dict[tuple[int, int], Counter] = defaultdict(Counter)
    for o in offers:
        bucket = counts[_month(o.created_at)]
        bucket["sent"] += 1
        if o.response is not None:
            bucket[o.response.value] += 1
    start = _month(since) if since else min(counts)
    end = _month(now)
    rows = []
    year, month = start
    while (year, month) <= end:
        c = counts.get((year, month), Counter())
        rows.append({
            "month": f"{year:04d}-{month:02d}",
            "sent": c["sent"],
            "accepted": c[OfferResponse.ACCEPTED.value],
            "declined": c[OfferResponse.DECLINED.value],
        })
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return rows


# ---------------------------------------------------------------------------
# CSV (§20.3)
# ---------------------------------------------------------------------------

def _cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.astimezone(TASHKENT).strftime("%Y-%m-%d %H:%M")
    text = str(value)
    # CSV/formula injection: foydalanuvchi matni Excel'da formula bo'lib ochilmasin
    return "'" + text if text.startswith(FORMULA_PREFIXES) else text


def write_csv(header: list[str], rows: Iterable[list]) -> str:
    buf = io.StringIO()
    buf.write("﻿")   # Excel UTF-8'ni shu belgi bilan taniydi
    writer = csv.writer(buf, lineterminator="\r\n")
    writer.writerow(header)
    for row in rows:
        writer.writerow([_cell(v) for v in row])
    return buf.getvalue()


def offers_csv(rows: list[OfferRow]) -> str:
    return write_csv(
        ["created_at", "position_title", "candidate_name", "status", "response",
         "respond_due_at", "responded_at", "response_hours", "candidate_email"],
        (
            [r.offer.created_at, r.offer.position_title, r.candidate_name, r.offer.status.value,
             r.offer.response.value if r.offer.response else None, r.offer.respond_due_at,
             r.offer.responded_at, response_hours(r.offer), r.candidate_email]
            for r in rows
        ),
    )


def candidates_csv(rows: list[tuple[str, Profile]]) -> str:
    keys = [c.value for c in Competency]
    return write_csv(
        ["full_name", "overall_score", "runs_completed", "sectors", *keys, "last_completed_at"],
        (
            [name, p.overall_score, len(p.runs), ", ".join(p.sectors),
             *(p.competencies.get(k) for k in keys), p.last_completed_at]
            for name, p in rows
        ),
    )
