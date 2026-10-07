"""Holat tekshiruvi (CONTRACT.md §18.1)."""
import pytest

from app.api.health import WORKER_KEY
from app.core.redis_client import redis_client


@pytest.fixture
async def worker_alive():
    await redis_client.set(WORKER_KEY, "Mar-01 12:00:00 j_complete=0", ex=61)
    yield
    await redis_client.delete(WORKER_KEY)


async def test_ok_when_everything_runs(client, worker_alive):
    r = await client.get("/api/v1/health")   # login'siz
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "db": True, "redis": True, "worker": True}


async def test_dead_worker_is_503(client):
    await redis_client.delete(WORKER_KEY)
    r = await client.get("/api/v1/health")
    assert r.status_code == 503
    assert r.json() == {"status": "degraded", "db": True, "redis": True, "worker": False}


async def test_redis_down_hides_details(client, monkeypatch, worker_alive):
    async def broken():
        raise ConnectionError("redis://secret-host:6379 refused")

    monkeypatch.setattr(redis_client, "ping", broken)
    r = await client.get("/api/v1/health")
    assert r.status_code == 503
    assert r.json() == {"status": "degraded", "db": True, "redis": False, "worker": False}
    assert "secret-host" not in r.text


def test_worker_reports_health_every_minute():
    from app.ai.worker import WorkerSettings

    assert WorkerSettings.health_check_interval == 60
