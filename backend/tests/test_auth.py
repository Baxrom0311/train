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
