"""
Platforma statistikasi (CONTRACT.md §21.3) — admin uchun, faqat o'qiydi.

Davr — oxirgi `days` Toshkent kuni (bugun ham). Yig'indilar SQL'da: Run va
javoblar soni pilotda ham minglab bo'ladi, hammasini xotiraga olib kelish shart emas.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta

from sqlalchemy import Date, Float, case, cast, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.usage import cost_usd, today
from app.models.ai_usage import AIUsage
from app.models.billing import Company, University
from app.models.enums import AIEvalStatus, RunStatus
from app.models.rbac import Role
from app.models.scenario import Run, Scenario, ScenarioVersion
from app.models.simulation import Submission
from app.models.user import User
from app.scenario.clock import TASHKENT

TOP_SCENARIOS = 10
FINISHED = (RunStatus.COMPLETED, RunStatus.EXPIRED, RunStatus.ABANDONED)


def _local_day(column):
    return cast(func.timezone(TASHKENT.key, column), Date)


def _pct(part: int, whole: int) -> float | None:
    return round(part * 100 / whole, 1) if whole else None


def _round(value: float | None, digits: int = 1) -> float | None:
    return round(value, digits) if value is not None else None


def _add_cost(acc: float | None, value: float | None) -> float | None:
    if value is None:
        return acc
    return (acc or 0.0) + value


def _score():
    return cast(Run.final_report["overall_score"].astext, Float)


def period(now: datetime, days: int) -> tuple[date, datetime]:
    """Birinchi kun va uning boshlanishi (UTC'ga o'girilgan Toshkent yarim tuni)."""
    first = today(now) - timedelta(days=days - 1)
    return first, datetime.combine(first, time.min, tzinfo=TASHKENT)


async def _users(db: AsyncSession, since: datetime) -> dict:
    students = (
        select(User.id)
        .join(Role, Role.id == User.role_id)
        .where(Role.name == "student", User.is_active.is_(True))
    )
    total = await db.scalar(select(func.count()).select_from(students.subquery()))
    new = await db.scalar(select(func.count()).select_from(students.where(User.created_at >= since).subquery()))
    active = await db.scalar(
        select(func.count(distinct(Run.user_id))).where(Run.last_activity_at >= since)
    )
    return {
        "students": total,
        "companies": await db.scalar(select(func.count()).where(Company.is_verified.is_(True))),
        "universities": await db.scalar(select(func.count()).where(University.is_verified.is_(True))),
        "new_students": new,
        "active_students": active,
    }


async def _runs(db: AsyncSession, since: datetime) -> dict:
    in_progress = await db.scalar(
        select(func.count()).where(Run.status.in_((RunStatus.SCHEDULED, RunStatus.ACTIVE)))
    )
    by_status = dict((await db.execute(
        select(Run.status, func.count()).where(Run.created_at >= since).group_by(Run.status)
    )).all())
    avg = await db.scalar(
        select(func.avg(_score())).where(Run.created_at >= since, Run.status == RunStatus.COMPLETED)
    )
    completed = by_status.get(RunStatus.COMPLETED, 0)
    finished = sum(by_status.get(s, 0) for s in FINISHED)
    return {
        "in_progress": in_progress,
        "started": sum(by_status.values()),
        "completed": completed,
        "expired": by_status.get(RunStatus.EXPIRED, 0),
        "abandoned": by_status.get(RunStatus.ABANDONED, 0),
        "completion_rate": _pct(completed, finished),
        "avg_score": _round(avg),
    }


async def _evaluation(db: AsyncSession, since: datetime, now: datetime, queue_jobs: int | None) -> dict:
    run_answers = Submission.run_id.is_not(None)
    waiting = (AIEvalStatus.PENDING, AIEvalStatus.QUEUED_RETRY)
    counts = dict((await db.execute(
        select(Submission.ai_eval_status, func.count())
        .where(run_answers, Submission.ai_eval_status.in_(waiting))
        .group_by(Submission.ai_eval_status)
    )).all())
    failed = await db.scalar(select(func.count()).where(
        run_answers, Submission.ai_eval_status == AIEvalStatus.FAILED_PERMANENT, Submission.submitted_at >= since,
    ))
    oldest = await db.scalar(
        select(func.min(Submission.submitted_at)).where(run_answers, Submission.ai_eval_status.in_(waiting))
    )
    return {
        "pending": counts.get(AIEvalStatus.PENDING, 0),
        "queued_retry": counts.get(AIEvalStatus.QUEUED_RETRY, 0),
        "failed": failed,
        "oldest_pending_minutes": max(0, int((now - oldest).total_seconds() // 60)) if oldest else None,
        "queue_jobs": queue_jobs,
    }


async def _ai(db: AsyncSession, first: date) -> tuple[dict, dict[date, dict]]:
    rows = (await db.execute(select(AIUsage).where(AIUsage.day >= first))).scalars().all()
    totals = {"calls": 0, "failures": 0, "tokens_in": 0, "tokens_out": 0, "cost_usd": None, "cost_complete": True}
    purposes: dict[str, dict] = defaultdict(lambda: {"calls": 0, "tokens": 0, "cost_usd": None})
    providers: dict[tuple[str, str], dict] = defaultdict(
        lambda: {"calls": 0, "failures": 0, "tokens_in": 0, "tokens_out": 0}
    )
    daily: dict[date, dict] = defaultdict(lambda: {"ai_tokens": 0, "ai_cost_usd": None})
    for r in rows:
        cost = cost_usd(r.provider, r.tokens_in, r.tokens_out)
        tokens = r.tokens_in + r.tokens_out
        if cost is None and tokens:
            totals["cost_complete"] = False
        for key in ("calls", "failures", "tokens_in", "tokens_out"):
            totals[key] += getattr(r, key)
            providers[(r.provider, r.model)][key] += getattr(r, key)
        totals["cost_usd"] = _add_cost(totals["cost_usd"], cost)
        p = purposes[r.purpose]
        p["calls"] += r.calls
        p["tokens"] += tokens
        p["cost_usd"] = _add_cost(p["cost_usd"], cost)
        d = daily[r.day]
        d["ai_tokens"] += tokens
        d["ai_cost_usd"] = _add_cost(d["ai_cost_usd"], cost)

    totals["cost_usd"] = _round(totals["cost_usd"], 4)
    totals["by_purpose"] = sorted(
        ({"purpose": k, **v, "cost_usd": _round(v["cost_usd"], 4)} for k, v in purposes.items()),
        key=lambda x: (-x["tokens"], x["purpose"]),
    )
    totals["by_provider"] = sorted(
        (
            {"provider": prov, "model": model, **v,
             "cost_usd": _round(cost_usd(prov, v["tokens_in"], v["tokens_out"]), 4)}
            for (prov, model), v in providers.items()
        ),
        key=lambda x: (-(x["tokens_in"] + x["tokens_out"]), x["provider"], x["model"]),
    )
    return totals, daily


async def _daily(db: AsyncSession, first: date, since: datetime, last: date, ai_daily: dict[date, dict]) -> list[dict]:
    async def per_day(column, *where) -> dict[date, int]:
        day = _local_day(column)
        return dict((await db.execute(select(day, func.count()).where(*where).group_by(day))).all())

    new_students = await per_day(
        User.created_at, User.created_at >= since, User.is_active.is_(True),
        User.role_id.in_(select(Role.id).where(Role.name == "student")),
    )
    started = await per_day(Run.created_at, Run.created_at >= since)
    completed = await per_day(Run.last_activity_at, Run.last_activity_at >= since, Run.status == RunStatus.COMPLETED)

    rows, day = [], first
    while day <= last:
        ai = ai_daily.get(day, {})
        rows.append({
            "day": day,
            "new_students": new_students.get(day, 0),
            "runs_started": started.get(day, 0),
            "runs_completed": completed.get(day, 0),
            "ai_tokens": ai.get("ai_tokens", 0),
            "ai_cost_usd": _round(ai.get("ai_cost_usd"), 4),
        })
        day += timedelta(days=1)
    return rows


async def _scenarios(db: AsyncSession, since: datetime) -> list[dict]:
    completed = Run.status == RunStatus.COMPLETED
    rows = (await db.execute(
        select(
            Scenario.id, Scenario.title, Scenario.sector,
            func.count(Run.id).label("started"),
            func.count(case((completed, 1))).label("completed"),
            func.count(case((Run.status.in_(FINISHED), 1))).label("finished"),
            func.avg(case((completed, _score()))).label("avg_score"),
        )
        .join(ScenarioVersion, ScenarioVersion.scenario_id == Scenario.id)
        .join(Run, Run.scenario_version_id == ScenarioVersion.id)
        .where(Run.created_at >= since)
        .group_by(Scenario.id, Scenario.title, Scenario.sector)
        .order_by(func.count(Run.id).desc(), Scenario.title)
        .limit(TOP_SCENARIOS)
    )).all()
    return [
        {
            "scenario_id": r.id, "title": r.title, "sector": r.sector.value,
            "started": r.started, "completed": r.completed,
            "completion_rate": _pct(r.completed, r.finished), "avg_score": _round(r.avg_score),
        }
        for r in rows
    ]


async def build(db: AsyncSession, days: int, now: datetime, queue_jobs: int | None) -> dict:
    first, since = period(now, days)
    ai, ai_daily = await _ai(db, first)
    return {
        "generated_at": now,
        "days": days,
        "users": await _users(db, since),
        "runs": await _runs(db, since),
        "evaluation": await _evaluation(db, since, now, queue_jobs),
        "ai": ai,
        "daily": await _daily(db, first, since, today(now), ai_daily),
        "scenarios": await _scenarios(db, since),
    }
