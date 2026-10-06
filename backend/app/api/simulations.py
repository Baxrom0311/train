import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.simulation import Simulation, SimulationTask
from app.core.deps import get_current_active_user, require_permission
from app.models.user import User

router = APIRouter(tags=["simulations"])

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
    
    class Config:
        from_attributes = True

class SimulationCreate(BaseModel):
    title: str
    description: str
    sector: str
    difficulty: str
    company_name: str
    tasks: list[TaskCreate]

class SimulationOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    sector: str
    difficulty: str
    company_name: str
    is_active: bool
    tasks: list[TaskOut] = []

    class Config:
        from_attributes = True


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

@router.post("/simulations", response_model=SimulationOut, status_code=status.HTTP_201_CREATED)
async def create_simulation(
    sim_in: SimulationCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("manage_simulations"))
):
    sim = Simulation(
        title=sim_in.title,
        description=sim_in.description,
        sector=sim_in.sector,
        difficulty=sim_in.difficulty,
        company_name=sim_in.company_name,
        created_by_admin_id=user.id
    )
    for i, t in enumerate(sim_in.tasks):
        task = SimulationTask(
            order_index=i,
            title=t.title,
            description=t.description,
            expected_skills=t.expected_skills
        )
        sim.tasks.append(task)

    db.add(sim)
    await db.commit()
    await db.refresh(sim)
    return sim

@router.put("/simulations/{id}", response_model=SimulationOut)
async def update_simulation(
    id: uuid.UUID,
    sim_in: SimulationCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("manage_simulations"))
):
    result = await db.execute(select(Simulation).where(Simulation.id == id))
    sim = result.scalars().first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    sim.title = sim_in.title
    sim.description = sim_in.description
    sim.sector = sim_in.sector
    sim.difficulty = sim_in.difficulty
    sim.company_name = sim_in.company_name

    # Remove old tasks
    for task in sim.tasks:
        await db.delete(task)
    
    # Needs a flush to avoid duplicate unique order_index if any, but let's just clear
    sim.tasks = []
    
    for i, t in enumerate(sim_in.tasks):
        task = SimulationTask(
            order_index=i,
            title=t.title,
            description=t.description,
            expected_skills=t.expected_skills
        )
        sim.tasks.append(task)

    await db.commit()
    await db.refresh(sim)
    return sim

@router.delete("/simulations/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_simulation(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("manage_simulations"))
):
    result = await db.execute(select(Simulation).where(Simulation.id == id))
    sim = result.scalars().first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    await db.delete(sim)
    await db.commit()
    return None
