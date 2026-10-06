import hmac
import hashlib
import html
import base64
import json
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from app.config import settings

# ── Universal Xavfsiz Parol Hashing (PBKDF2-HMAC-SHA256) ──────────────────
def get_password_hash(password: str) -> str:
    salt = "tryjob_salt_2026_uzbekistan"
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return key.hex()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    expected = get_password_hash(plain_password)
    return hmac.compare_digest(expected, hashed_password)

# ── Universal JWT Token Generatori va Validatori ──────────────────────────
def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')

def _base64url_decode(data_str: str) -> bytes:
    padding = '=' * (4 - (len(data_str) % 4))
    return base64.urlsafe_b64decode((data_str + padding).encode('ascii'))

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    to_encode = data.copy()
    if expires_delta:
        expire_ts = int(time.time() + expires_delta.total_seconds())
    else:
        expire_ts = int(time.time() + settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    to_encode.update({"exp": expire_ts, "token_type": "access"})

    header_b64 = _base64url_encode(json.dumps(header, separators=(',', ':')).encode('utf-8'))
    payload_b64 = _base64url_encode(json.dumps(to_encode, separators=(',', ':')).encode('utf-8'))
    
    signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
    signature = hmac.new(settings.SECRET_KEY.encode('utf-8'), signing_input, hashlib.sha256).digest()
    sig_b64 = _base64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"

def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    to_encode = data.copy()
    if expires_delta:
        expire_ts = int(time.time() + expires_delta.total_seconds())
    else:
        expire_ts = int(time.time() + settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400)
    to_encode.update({"exp": expire_ts, "token_type": "refresh"})

    header_b64 = _base64url_encode(json.dumps(header, separators=(',', ':')).encode('utf-8'))
    payload_b64 = _base64url_encode(json.dumps(to_encode, separators=(',', ':')).encode('utf-8'))
    
    signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
    signature = hmac.new(settings.SECRET_KEY.encode('utf-8'), signing_input, hashlib.sha256).digest()
    sig_b64 = _base64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"

def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """JWT token imzosini va amal qilish muddatini tekshirish."""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        
        # Imzoni tekshirish
        signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
        expected_sig = hmac.new(settings.SECRET_KEY.encode('utf-8'), signing_input, hashlib.sha256).digest()
        actual_sig = _base64url_decode(sig_b64)
        
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        payload_bytes = _base64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode('utf-8'))

        # Muddati o'tganligini tekshirish
        exp = payload.get("exp")
        if exp and exp < time.time():
            return None

        return payload
    except Exception:
        return None

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Faqat access_token turlariga ruxsat berish."""
    payload = decode_token(token)
    if not payload:
        return None
    if payload.get("token_type") != "access":
        return None
    return payload

def decode_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    """Faqat refresh_token turlariga ruxsat berish."""
    payload = decode_token(token)
    if not payload:
        return None
    if payload.get("token_type") != "refresh":
        return None
    return payload

# ── Sertifikat HMAC-SHA256 ────────────────────────────────────────────────
def generate_cert_hmac(cert_uuid: str, user_id: str, simulation_id: str, score: float) -> str:
    message = f"{cert_uuid}:{user_id}:{simulation_id}:{score:.2f}".encode('utf-8')
    return hmac.new(settings.HMAC_CERT_SECRET.encode('utf-8'), message, hashlib.sha256).hexdigest()

def verify_cert_hmac(cert_uuid: str, user_id: str, simulation_id: str, score: float, signature: str) -> bool:
    expected_sig = generate_cert_hmac(cert_uuid, user_id, simulation_id, score)
    return hmac.compare_digest(expected_sig, signature)

# ── Sanitization ──────────────────────────────────────────────────────────
def sanitize_text(text: Optional[str]) -> str:
    if not text:
        return ""
    return html.escape(text.strip())
