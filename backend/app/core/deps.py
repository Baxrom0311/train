from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.rbac import Permission

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    """
    Faqat 'access' token_type'ga ega tokenlarni qabul qiladi.
    Refresh token bilan kirmoqchi bo'lsa — 401 qaytariladi.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        # token_type tekshiruvi: faqat 'access' token qabul qilinadi
        token_type: str = payload.get("token_type")
        if token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token cannot be used as access token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def require_permission(key: str):
    async def permission_checker(current_user: User = Depends(get_current_active_user)):
        role = current_user.role
        if not role:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        permissions = [p.key for p in role.permissions]
        if key not in permissions:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        return current_user
    return permission_checker


def rate_limit(action: str, max_requests: int = 10, window_seconds: int = 60, fail_closed: bool = False):
    """
    Redis-asosida rate-limiting dependency factory.
    key format: rate_limit:{action}:{user_id}:{current_minute_window}

    :param fail_closed: Redis ishlamay qolsa nima qilish kerak.
        False (default) — o'tkazib yuborish (fail-open): oddiy UX-darajadagi
        cheklovlar uchun (masalan API spam'ini kamaytirish) — Redis vaqtincha
        ishlamay qolgani butun platformani to'xtatib qo'ymasin.
        True — rad etish (fail-closed): rate-limit o'zi xavfsizlik nazorati
        bo'lgan joylarda (masalan `/tools/sandbox` — bu auth'siz/ nazoratsiz
        kod bajarish yukini cheklaydi) Redis ishlamay qolgani "cheksiz
        so'rov qabul qilish" degani bo'lmasligi kerak.
    """
    async def _rate_limiter(current_user: User = Depends(get_current_active_user)):
        from app.core.redis_client import redis_client
        import time

        window = int(time.time() // window_seconds)
        key = f"rate_limit:{action}:{current_user.id}:{window}"

        try:
            count = await redis_client.incr(key)
            if count == 1:
                # Birinchi so'rov — TTL o'rnatamiz
                await redis_client.expire(key, window_seconds)
            if count > max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded: max {max_requests} requests per {window_seconds}s",
                )
        except HTTPException:
            raise
        except Exception:
            if fail_closed:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Rate limiting service unavailable; request rejected for safety.",
                )
            # Redis ishlamay qolsa — bloklashdan ko'ra o'tkazib yuborish (fail open)
            pass

        return current_user

    return _rate_limiter
