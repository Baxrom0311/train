"""Talaba analitikasi API (CONTRACT.md §17.2) — faqat o'z Run'lari."""
import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.student import load
from app.core.deps import get_current_active_user
from app.database import get_db
from app.models.user import User

Trend = Literal["up", "down", "flat", "new"]

users_router = APIRouter(prefix="/api/v1/users", tags=["analytics"])


class Summary(BaseModel):
    completed: int
    in_progress: int
    avg_score: float | None
    best_score: float | None
    on_time_rate: float | None
    certificates: int


class TimelinePoint(BaseModel):
    run_id: uuid.UUID
    scenario_title: str
    sector: str
    completed_at: datetime
    overall_score: float | None
    on_time_rate: float | None
    competency_scores: dict[str, float]


class CompetencyTrend(BaseModel):
    key: str
    current: float
    first: float
    delta: float | None
    trend: Trend
    values: list[float]


class SectorStat(BaseModel):
    sector: str
    runs: int
    avg_score: float | None


class Focus(BaseModel):
    key: str
    current: float
    trend: Trend


class Recommendation(BaseModel):
    scenario_id: uuid.UUID
    title: str
    sector: str
    company_name: str
    duration_days: int
    difficulty: str
    practices: dict[str, int]


class AnalyticsOut(BaseModel):
    summary: Summary
    timeline: list[TimelinePoint]
    competencies: list[CompetencyTrend]
    sectors: list[SectorStat]
    focus: list[Focus]
    improvements: list[str]
    recommendations: list[Recommendation]


@users_router.get("/me/analytics", response_model=AnalyticsOut)
async def my_analytics(
    me: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    a = await load(db, me.id)
    return AnalyticsOut(
        summary=Summary(**a.summary),
        timeline=[TimelinePoint.model_validate(p, from_attributes=True) for p in a.timeline],
        competencies=a.competencies,
        sectors=a.sectors,
        focus=a.focus,
        improvements=a.improvements,
        recommendations=a.recommendations,
    )
