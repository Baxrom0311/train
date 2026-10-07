import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_register_student(client: AsyncClient):
    response = await client.post("/api/v1/auth/register", json={
        "email": "student@example.com",
        "password": "strongpassword",
        "full_name": "Test Student"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data

@pytest.mark.asyncio
async def test_login(client: AsyncClient, test_user_factory):
    await test_user_factory("login@example.com", "mypassword")
    
    response = await client.post("/api/v1/auth/login", data={
        "username": "login@example.com",
        "password": "mypassword"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

@pytest.mark.asyncio
async def test_me(client: AsyncClient, test_user_factory):
    user = await test_user_factory("me@example.com", "mypass")
    
    login_resp = await client.post("/api/v1/auth/login", data={
        "username": "me@example.com",
        "password": "mypass"
    })
    token = login_resp.json()["access_token"]
    
    response = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.com"
    assert data["role"] == "student"

@pytest.mark.asyncio
async def test_refresh(client: AsyncClient, test_user_factory):
    await test_user_factory("refresh@example.com", "mypass")
    
    login_resp = await client.post("/api/v1/auth/login", data={
        "username": "refresh@example.com",
        "password": "mypass"
    })
    refresh_token = login_resp.json()["refresh_token"]
    
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()


# ===========================================================
# Token type xavfsizlik testlari
# ===========================================================

@pytest.mark.asyncio
async def test_refresh_token_rejected_as_access_token(client: AsyncClient, test_user_factory):
    """
    Refresh token bilan himoyalangan endpoint'ga (GET /users/me) kirish → 401.
    Bu token_type='refresh' != 'access' tekshiruvining isboti.
    """
    await test_user_factory("tokentype1@example.com", "mypass")
    login_resp = await client.post("/api/v1/auth/login", data={
        "username": "tokentype1@example.com",
        "password": "mypass"
    })
    tokens = login_resp.json()
    refresh_token = tokens["refresh_token"]

    # Refresh tokenni access token o'rnida ishlatish — RAD etilishi kerak
    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )
    assert response.status_code == 401, (
        f"Refresh token access token o'rnida ishlatilishi kerak emas! "
        f"Actual: {response.status_code}"
    )


@pytest.mark.asyncio
async def test_access_token_rejected_in_refresh_endpoint(client: AsyncClient, test_user_factory):
    """
    Access token bilan /auth/refresh endpoint'ga so'rov → 401.
    """
    await test_user_factory("tokentype2@example.com", "mypass")
    login_resp = await client.post("/api/v1/auth/login", data={
        "username": "tokentype2@example.com",
        "password": "mypass"
    })
    access_token = login_resp.json()["access_token"]

    # Access tokenni refresh token o'rnida ishlatish — RAD etilishi kerak
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access_token},
    )
    assert response.status_code == 401, (
        f"Access token refresh token o'rnida ishlatilishi kerak emas! "
        f"Actual: {response.status_code}"
    )


@pytest.mark.asyncio
async def test_tokens_have_different_types(client: AsyncClient, test_user_factory):
    """
    Login javobi ham access, ham refresh tokenni o'z ichiga olishi kerak.
    Ikkalasi decode qilinganda token_type farq qilishi kerak.
    """
    from jose import jwt
    from app.config import settings

    await test_user_factory("tokentype3@example.com", "mypass")
    login_resp = await client.post("/api/v1/auth/login", data={
        "username": "tokentype3@example.com",
        "password": "mypass"
    })
    tokens = login_resp.json()

    access_payload = jwt.decode(
        tokens["access_token"], settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
    )
    refresh_payload = jwt.decode(
        tokens["refresh_token"], settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
    )

    assert access_payload.get("token_type") == "access"
    assert refresh_payload.get("token_type") == "refresh"
    assert access_payload.get("token_type") != refresh_payload.get("token_type")

