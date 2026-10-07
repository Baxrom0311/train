import redis.asyncio as redis
from arq import create_pool
from arq.connections import RedisSettings
from app.config import settings

redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)

_arq_pool = None


async def get_arq_pool():
    """
    arq ish navbati pool'ini olish (lazy, keshlangan). `redis_client`dan
    FARQLI — `arq.enqueue_job(...)` metodini faqat shu pool beradi, oddiy
    `redis.asyncio` klienti bunday metodga ega emas (avvalgi versiyada
    oddiy redis_client'ni evaluate_submission'ga uzatish rejalashtirilgan
    edi, lekin bu runtime xato berardi).
    """
    global _arq_pool
    if _arq_pool is None:
        _arq_pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    return _arq_pool
