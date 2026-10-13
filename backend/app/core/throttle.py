"""
Redis hisoblagichlari bilan urinishlarni cheklash (CONTRACT.md §30.4).

Oyna qat'iy: kalit birinchi hisobda `window` TTL bilan yaratiladi va shu
vaqt o'tgach yo'qoladi. Redis ishlamasa — fail-open (log `warning`): login
butun platforma uchun to'xtab qolmasin, parol bcrypt bilan baribir sekin.

`deps.rate_limit` (foydalanuvchi bo'yicha, har daqiqa) dan farqi: bu yerda
kalit ixtiyoriy (email, IP), tekshirish va hisoblash alohida — login faqat
xatoni sanaydi va chegarada parolni tekshirmasdan rad etadi.
"""
import logging
from dataclasses import dataclass

from fastapi import HTTPException, Request, status

log = logging.getLogger(__name__)

PREFIX = "throttle:"


@dataclass(frozen=True)
class Limit:
    key: str      # PREFIX'siz, masalan "login:fail:ip:1.2.3.4"
    max: int
    window: int   # soniya

    @property
    def redis_key(self) -> str:
        return PREFIX + self.key


def client_ip(request: Request) -> str:
    """uvicorn `--proxy-headers` bilan — nginx qayta yozgan haqiqiy mijoz IP'si (§30.4)."""
    return request.client.host if request.client else "unknown"


def too_many(retry_after: int) -> HTTPException:
    retry_after = max(1, retry_after)
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={"code": "too_many_attempts", "retry_after": retry_after},
        headers={"Retry-After": str(retry_after)},
    )


def _redis():
    from app.core.redis_client import redis_client
    return redis_client


async def retry_after(limits: list[Limit]) -> int | None:
    """Chegaraga yetgan kalit bo'lsa — kutish soniyasi (eng uzog'i), aks holda None."""
    try:
        r = _redis()
        counts = await r.mget([lim.redis_key for lim in limits])
        waits = []
        for lim, count in zip(limits, counts):
            if count is not None and int(count) >= lim.max:
                ttl = await r.ttl(lim.redis_key)
                waits.append(ttl if ttl > 0 else lim.window)
        return max(waits) if waits else None
    except Exception as exc:  # noqa: BLE001 — Redis yo'q: fail-open
        log.warning("throttle tekshirilmadi (Redis): %s", exc)
        return None


async def _incr(limits: list[Limit]) -> list[tuple[int, int]] | None:
    """Har kalitga +1 → [(hisob, TTL)]; yangi kalit `window` TTL bilan (SET NX EX + INCR — TTL'siz kalit qolmaydi)."""
    try:
        async with _redis().pipeline(transaction=True) as pipe:
            for lim in limits:
                pipe.set(lim.redis_key, 0, ex=lim.window, nx=True)
                pipe.incr(lim.redis_key)
                pipe.ttl(lim.redis_key)
            res = await pipe.execute()
        return [(int(res[i + 1]), int(res[i + 2])) for i in range(0, len(res), 3)]
    except Exception as exc:  # noqa: BLE001
        log.warning("throttle hisoblanmadi (Redis): %s", exc)
        return None


async def hit(limits: list[Limit]) -> None:
    await _incr(limits)


async def clear(limits: list[Limit]) -> None:
    try:
        await _redis().delete(*[lim.redis_key for lim in limits])
    except Exception as exc:  # noqa: BLE001
        log.warning("throttle tozalanmadi (Redis): %s", exc)


async def consume(limits: list[Limit]) -> None:
    """Har so'rov hisoblanadigan amallar (forgot, resend, register): +1, chegaradan oshsa 429."""
    counted = await _incr(limits)
    if counted is None:
        return
    waits = [ttl if ttl > 0 else lim.window for lim, (count, ttl) in zip(limits, counted) if count > lim.max]
    if waits:
        raise too_many(max(waits))
