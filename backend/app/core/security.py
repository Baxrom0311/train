from datetime import datetime, timedelta, timezone
from typing import Any, Union
from jose import jwt
from passlib.context import CryptContext
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode = {
        "exp": expire,
        "iat": now.timestamp(),  # §30.3: kasr soniya — parol almashgan paytdan aniq oldin/keyin
        "sub": str(subject),
        "token_type": "access",  # Token turi: access — xavfsizlik uchun
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: Union[str, Any]) -> str:
    now = datetime.now(timezone.utc)
    to_encode = {
        "exp": now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": now.timestamp(),
        "sub": str(subject),
        "token_type": "refresh",  # Token turi: refresh — access o'rnida ishlatib bo'lmaydi
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def issued_after_password_change(payload: dict, password_changed_at: datetime | None) -> bool:
    """
    JWT parol oxirgi marta almashgandan keyin berilganmi (CONTRACT.md §30.3).
    `iat` kasr soniyali (NumericDate ruxsat beradi) — tiklashdan bir lahza
    oldin olingan token ham rad etiladi; `iat`siz (eski) token parol
    almashgan foydalanuvchida rad etiladi.
    """
    if password_changed_at is None:
        return True
    iat = payload.get("iat")
    if not isinstance(iat, (int, float)):
        return False
    return iat >= password_changed_at.timestamp()
