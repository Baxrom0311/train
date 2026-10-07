"""
Run bildirishnomalari → Redis pub/sub `run:{id}` (CONTRACT.md §9.8).

Worker va API alohida jarayonlar; SSE endpoint shu kanalga obuna bo'ladi.
Commit'dan **keyin** chaqiriladi. Redis ishlamasa bildirishnoma yo'qoladi,
lekin holat DB'da — talaba keyingi so'rovda ko'radi.
"""

import json
import logging

from app.scenario.engine import Note

log = logging.getLogger(__name__)


def channel(run_id) -> str:
    return f"run:{run_id}"


async def publish(notes: list[Note], redis=None) -> None:
    if not notes:
        return
    if redis is None:
        from app.core.redis_client import redis_client as redis
    for note in notes:
        try:
            await redis.publish(channel(note.run_id), json.dumps({"type": note.type, **note.data}))
        except Exception as exc:  # noqa: BLE001
            log.warning("run bildirishnomasi yuborilmadi (%s): %s", note.run_id, exc)
            return
