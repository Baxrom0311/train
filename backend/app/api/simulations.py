import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.simulation import Simulation
from app.models.enums import Sector
from app.core.deps import get_current_active_user, require_permission
from app.models.user import User

router = APIRouter(tags=["simulations"])

# FROZEN (CONTRACT.md §9.0 Q2): eski "topshiriqlar ro'yxati" simulyatsiyalariga
# yangi kontent qo'shilmaydi — o'qish ishlaydi, yozish 410. Yangi kontent:
# ssenariylar (`tools/import_scenario.py`, §9.3). Ruxsat tekshiruvi saqlanadi,
# shunda ruxsatsiz foydalanuvchi baribir 403 oladi.
_FROZEN = HTTPException(
    status_code=status.HTTP_410_GONE,
    detail="Legacy simulations are frozen; new content is published as scenarios (CONTRACT.md §9).",
)

# Schemas
class TaskCreate(BaseModel):
    title: str
    description: str
    expected_skills: list[str]

class TaskOut(BaseModel):
    id: uuid.UUID
    order_index: int
    title: str
    description: str
    expected_skills: list[str]
    
    model_config = ConfigDict(from_attributes=True)

class SimulationCreate(BaseModel):
    title: str
    description: str
    sector: Sector
    difficulty: str
    company_name: str
    tasks: list[TaskCreate]

class SimulationOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    sector: Sector
    difficulty: str
    company_name: str
    is_active: bool
    tasks: list[TaskOut] = []

    model_config = ConfigDict(from_attributes=True)


@router.get("/simulations", response_model=List[SimulationOut])
async def list_simulations(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(Simulation).where(Simulation.is_active == True))
    return result.scalars().all()

@router.get("/simulations/{id}", response_model=SimulationOut)
async def get_simulation(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user)
):
    result = await db.execute(select(Simulation).where(Simulation.id == id))
    sim = result.scalars().first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return sim

@router.post("/simulations", status_code=status.HTTP_410_GONE)
async def create_simulation(
    sim_in: SimulationCreate,
    user: User = Depends(require_permission("manage_simulations"))
):
    raise _FROZEN

@router.put("/simulations/{id}", status_code=status.HTTP_410_GONE)
async def update_simulation(
    id: uuid.UUID,
    sim_in: SimulationCreate,
    user: User = Depends(require_permission("manage_simulations"))
):
    raise _FROZEN

@router.delete("/simulations/{id}", status_code=status.HTTP_410_GONE)
async def delete_simulation(
    id: uuid.UUID,
    user: User = Depends(require_permission("manage_simulations"))
):
    raise _FROZEN
