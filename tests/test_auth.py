import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
    create_refresh_token,
    decode_refresh_token
)

client = TestClient(app)

def test_password_hashing():
    pwd = "superSecretPassword123"
    hashed = get_password_hash(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("wrongPassword", hashed) is False

def test_jwt_token_cycle():
    payload = {"sub": "user-12345", "role": "student"}
    access_tok = create_access_token(payload)
    refresh_tok = create_refresh_token(payload)

    # 1. Access token tekshiruvi
    decoded_access = decode_access_token(access_tok)
    assert decoded_access is not None
    assert decoded_access["sub"] == "user-12345"
    assert decoded_access["role"] == "student"

    # 2. Refresh tokenni access sifatida qabul qilmaslik
    assert decode_access_token(refresh_tok) is None

    # 3. Access tokenni refresh sifatida qabul qilmaslik
    assert decode_refresh_token(access_tok) is None

    # 4. Refresh token to'g'ri dekodlanishi
    decoded_refresh = decode_refresh_token(refresh_tok)
    assert decoded_refresh is not None
    assert decoded_refresh["token_type"] == "refresh"

def test_register_and_login_api():
    import uuid
    unique_email = f"test_{uuid.uuid4().hex[:6]}@tryjob.uz"
    
    # 1. Register
    reg_resp = client.post("/api/v1/auth/register", json={
        "email": unique_email,
        "full_name": "Test Foydalanuvchi",
        "password": "mySecurePassword123",
        "university": "TATU"
    })
    assert reg_resp.status_code == 200
    data = reg_resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == unique_email

    # 2. Login
    login_resp = client.post("/api/v1/auth/login", json={
        "email": unique_email,
        "password": "mySecurePassword123"
    })
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert "access_token" in login_data
    assert "refresh_token" in login_data
    refresh_tok = login_data["refresh_token"]

    # 3. Refresh Token Endpoint
    refresh_resp = client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_tok
    })
    assert refresh_resp.status_code == 200
    refreshed_data = refresh_resp.json()
    assert "access_token" in refreshed_data
    assert "refresh_token" in refreshed_data

    # 4. Invalid Refresh Token rejection
    bad_resp = client.post("/api/v1/auth/refresh", json={
        "refresh_token": "invalid.refresh.token.string"
    })
    assert bad_resp.status_code == 401

