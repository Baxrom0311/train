"""
Ssenariylar katalogi va ish kalendari boshqaruvi (CONTRACT.md §9.9, Modul 9).

Katalogda faqat `published` versiyasi bor, `is_active` ssenariylar.
Personajlarning faqat ommaviy maydonlari (ism, rol) ko'rsatiladi —
`knows`/`secrets`, rubrika, hint va namunaviy javob hech qachon chiqmaydi.
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import extract, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user, require_permission
from app.database import get_db
from app.models.enums import HolidaySource, ScenarioVersionStatus, Sector
from app.models.scenario import Scenario, ScenarioVersion, WorkHoliday
from app.models.user import User
from app.scenario.engine import definition_for

router = APIRouter(tags=["scenarios"])


class PersonaPublic(BaseModel):
    key: str
    name: str
    role: str
    kind: str


class ScenarioOut(BaseModel):
    id: uuid.UUID
    slug: str
    title: str
    sector: Sector
    company_name: str
    difficulty: str
    duration_days: int
    version: int


class ScenarioDetailOut(ScenarioOut):
    personas: list[PersonaPublic]


class HolidayIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class HolidayOut(BaseModel):
    date: date
    name: str
    source: HolidaySource

    model_config = ConfigDict(from_attributes=True)


def _out(scenario: Scenario, version: ScenarioVersion) -> dict:
    return {
        "id": scenario.id,
        "slug": scenario.slug,
        "title": scenario.title,
        "sector": scenario.sector,
        "company_name": scenario.company_name,
        "difficulty": scenario.difficulty,
        "duration_days": scenario.duration_days,
        "version": version.version,
    }


def _published():
    return (
        select(Scenario, ScenarioVersion)
        .join(ScenarioVersion, ScenarioVersion.scenario_id == Scenario.id)
        .where(Scenario.is_active.is_(True), ScenarioVersion.status == ScenarioVersionStatus.PUBLISHED)
    )


async def published_version(db: AsyncSession, scenario_id: uuid.UUID) -> tuple[Scenario, ScenarioVersion]:
    row = (await db.execute(_published().where(Scenario.id == scenario_id))).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return row[0], row[1]


@router.get("/scenarios", response_model=list[ScenarioOut])
async def list_scenarios(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    rows = (await db.execute(_published().order_by(Scenario.title))).all()
    return [_out(s, v) for s, v in rows]


@router.get("/scenarios/{scenario_id}", response_model=ScenarioDetailOut)
async def get_scenario(
    scenario_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    scenario, version = await published_version(db, scenario_id)
    defn = definition_for(version)
    personas = [
        PersonaPublic(key=p.key, name=p.name, role=p.role, kind=p.kind.value) for p in defn.personas
    ]
    return {**_out(scenario, version), "personas": personas}


# ── Ish kalendari: bayramlar (§9.2) ───────────────────────────────────


@router.get("/admin/holidays", response_model=list[HolidayOut])
async def list_holidays(
    year: int | None = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("manage_simulations")),
):
    q = select(WorkHoliday).order_by(WorkHoliday.date)
    if year is not None:
        q = q.where(extract("year", WorkHoliday.date) == year)
    return (await db.execute(q)).scalars().all()


@router.put("/admin/holidays/{day}", response_model=HolidayOut)
async def put_holiday(
    day: date,
    body: HolidayIn,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("manage_simulations")),
):
    holiday = await db.get(WorkHoliday, day)
    if holiday is None:
        holiday = WorkHoliday(date=day)
        db.add(holiday)
    holiday.name = body.name
    holiday.source = HolidaySource.MANUAL
    await db.commit()
    return holiday


@router.delete("/admin/holidays/{day}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_holiday(
    day: date,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_permission("manage_simulations")),
):
    holiday = await db.get(WorkHoliday, day)
    if holiday is None:
        raise HTTPException(status_code=404, detail="Holiday not found")
    await db.delete(holiday)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
