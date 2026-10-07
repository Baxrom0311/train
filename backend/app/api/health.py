"""
Holat tekshiruvi (CONTRACT.md §18.1) — ochiq, compose healthcheck va uptime monitor uchun.

Faqat `bool`lar qaytadi: xato matni, versiya yoki ichki manzil chiqmaydi.
"""
import asyncio
import logging

from arq.constants import default_queue_name, health_check_key_suffix
from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

router = APIRouter(prefix="/api/v1", tags=["health"])
log = logging.getLogger(__name__)

TIMEOUT = 2.0   # soniya — monitor osilib qolmasin
WORKER_KEY = default_queue_name + health_check_key_suffix


class Health(BaseModel):
    status: str
    db: bool
    redis: bool
    worker: bool


async def _check(name: str, probe) -> bool:
    try:
        await asyncio.wait_for(probe, TIMEOUT)
        return True
    except Exception as exc:  # noqa: BLE001 — har qanday nosozlik "ishlamayapti" degani
        log.warning("health: %s ishlamayapti: %s", name, exc)
        return False


async def _worker_alive(redis) -> None:
    if not await redis.exists(WORKER_KEY):
        raise RuntimeError("arq health-check kaliti yo'q")


@router.get("/health", response_model=Health)
async def health(response: Response, db: AsyncSession = Depends(get_db)):
    from app.core.redis_client import redis_client as redis

    db_ok = await _check("db", db.execute(text("SELECT 1")))
    redis_ok = await _check("redis", redis.ping())
    worker_ok = redis_ok and await _check("worker", _worker_alive(redis))
    ok = db_ok and redis_ok and worker_ok
    if not ok:
        response.status_code = 503
    return Health(status="ok" if ok else "degraded", db=db_ok, redis=redis_ok, worker=worker_ok)
