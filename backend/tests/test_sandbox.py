"""
test_sandbox.py — Sandbox va /tools/sandbox endpoint testlari.

Tekshiriladigan holatlar:
1. Auth'siz so'rov → 401
2. 11-so'rovda rate-limit → 429
3. timeout_seconds=9999 → server haqiqatan ≤3s ishlatadi
4. AST: taqiqlangan modul import → xavfsizlik xatosi
5. AST: eval() chaqiruvi → xavfsizlik xatosi
6. AST: __class__ atributi → xavfsizlik xatosi
7. 'builtins' (ko'plik) taqiqlangan
8. Oddiy kod muvaffaqiyatli bajariladi
9. Syntax xatosi aniqlanadi
10. Haqiqiy timeout (subprocess)
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient

from app.core.sandbox import (
    validate_code,
    run_code,
    SecurityViolation,
    BANNED_MODULES,
    BANNED_CALLS,
    BANNED_ATTRS,
)


# ===========================================================
# 1. Unit testlar: sandbox.py (validate_code, run_code)
# ===========================================================

class TestValidateCode:
    """AST validatsiya unit testlari."""

    def test_safe_code_passes(self):
        """Oddiy xavfsiz kod — xato ko'tarmasligi kerak."""
        validate_code("x = 2 + 2\nprint(x)")

    # --- BANNED_MODULES ---
    @pytest.mark.parametrize("module", [
        "os", "sys", "subprocess", "shutil", "socket",
        "http", "requests", "urllib", "ctypes", "pathlib",
        "builtins",   # ko'plik bilan — 'builtin' emas!
        "importlib", "posix",
    ])
    def test_banned_module_import(self, module):
        with pytest.raises(SecurityViolation, match="Taqiqlangan modul"):
            validate_code(f"import {module}")

    def test_banned_module_from_import(self):
        with pytest.raises(SecurityViolation):
            validate_code("from os import path")

    def test_banned_module_submodule(self):
        with pytest.raises(SecurityViolation):
            validate_code("import os.path")

    # --- BANNED_CALLS ---
    @pytest.mark.parametrize("call", [
        "eval", "exec", "open", "compile", "__import__",
        "globals", "locals", "getattr", "setattr", "delattr", "breakpoint",
    ])
    def test_banned_call(self, call):
        with pytest.raises(SecurityViolation, match="Taqiqlangan funksiya"):
            validate_code(f"{call}('test')")

    # --- BANNED_ATTRS ---
    @pytest.mark.parametrize("attr", [
        "__class__", "__subclasses__", "__bases__", "__base__",
        "__globals__", "__builtins__", "__code__", "__closure__",
        "__dict__", "__mro__",
    ])
    def test_banned_attr(self, attr):
        with pytest.raises(SecurityViolation, match="Taqiqlangan atribut"):
            validate_code(f"x = obj.{attr}")

    def test_syntax_error(self):
        with pytest.raises(SyntaxError):
            validate_code("def broken(:")

    def test_builtins_plural_banned(self):
        """'builtins' (ko'plik) taqiqlangan, lekin 'builtin' (yakka) emas."""
        with pytest.raises(SecurityViolation):
            validate_code("import builtins")

    def test_nested_banned_call(self):
        """Murakkab ifodada ham topilishi kerak."""
        with pytest.raises(SecurityViolation):
            validate_code("result = [eval(x) for x in items]")


class TestRunCode:
    """run_code() funktsiyasi testlari."""

    def test_simple_code_runs(self):
        result = run_code("print('hello')")
        assert result.success is True
        assert "hello" in result.stdout

    def test_arithmetic(self):
        result = run_code("x = 6 * 7\nprint(x)")
        assert result.success is True
        assert "42" in result.stdout

    def test_banned_code_blocked(self):
        result = run_code("import os")
        assert result.success is False
        assert result.error is not None
        assert "Xavfsizlik xatosi" in result.error

    def test_timeout_capped_at_3_seconds(self):
        """timeout_seconds=9999 berilsa ham run_code 3.0s dan oshmasin."""
        # Cheksiz loop — timeout bilan to'xtatilishi kerak
        result = run_code("while True: pass", timeout=9999.0)
        assert result.success is False
        assert result.error is not None
        assert "Timeout" in result.error

    def test_actual_timeout_under_3s(self):
        """Haqiqiy bajarish vaqti 3.0s dan oshmasligi."""
        import time
        start = time.monotonic()
        run_code("while True: pass", timeout=9999.0)
        elapsed = time.monotonic() - start
        # 3.0s + 1.0s xatolik marjasi
        assert elapsed < 4.5, f"Timeout 3s'dan katta: {elapsed:.2f}s"

    def test_syntax_error_returns_error(self):
        result = run_code("def bad(:")
        assert result.success is False
        assert "Syntax xatosi" in result.error


# ===========================================================
# 2. Integration testlar: /tools/sandbox endpoint
# ===========================================================

@pytest.fixture
def mock_redis_ok():
    """Redis'ni simulyatsiya qiluvchi — rate-limit o'tkazib yuboradi."""
    with patch("app.core.redis_client.redis_client") as mock_redis:
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock(return_value=True)
        yield mock_redis


@pytest.fixture
def mock_redis_rate_limited():
    """Redis'ni 11-so'rovda 429 qaytarish uchun simulyatsiya qiladi."""
    with patch("app.core.redis_client.redis_client") as mock_redis:
        mock_redis.incr = AsyncMock(return_value=11)  # limit=10, bu 11-so'rov
        mock_redis.expire = AsyncMock(return_value=True)
        yield mock_redis


@pytest.mark.asyncio
async def test_sandbox_no_auth(client: AsyncClient):
    """Auth'siz so'rov → 401."""
    response = await client.post(
        "/api/v1/tools/sandbox",
        json={"code": "print('hello')", "timeout_seconds": 2.0},
    )
    assert response.status_code == 401, (
        f"Auth'siz sandbox so'rovi 401 qaytarmadi! Actual: {response.status_code}"
    )


@pytest.mark.asyncio
async def test_sandbox_with_auth_success(client: AsyncClient, test_user_factory, mock_redis_ok):
    """To'g'ri auth bilan oddiy kod muvaffaqiyatli bajariladi."""
    await test_user_factory("sandbox_ok@example.com", "testpass123")
    login = await client.post("/api/v1/auth/login", data={
        "username": "sandbox_ok@example.com",
        "password": "testpass123",
    })
    token = login.json()["access_token"]

    response = await client.post(
        "/api/v1/tools/sandbox",
        json={"code": "print('42')", "timeout_seconds": 2.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "42" in data["stdout"]


@pytest.mark.asyncio
async def test_sandbox_rate_limit_11th_request(client: AsyncClient, test_user_factory, mock_redis_rate_limited):
    """11-so'rovda rate-limit → 429."""
    await test_user_factory("sandbox_rl@example.com", "testpass123")
    login = await client.post("/api/v1/auth/login", data={
        "username": "sandbox_rl@example.com",
        "password": "testpass123",
    })
    token = login.json()["access_token"]

    response = await client.post(
        "/api/v1/tools/sandbox",
        json={"code": "print('x')", "timeout_seconds": 2.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 429, (
        f"11-so'rovda 429 qaytarmadi! Actual: {response.status_code}"
    )


@pytest.mark.asyncio
async def test_sandbox_timeout_capped_server_side(client: AsyncClient, test_user_factory, mock_redis_ok):
    """
    Client timeout_seconds=9999 yuborganda server haqiqatan ≤3s cheklov qo'yadi.
    actual_timeout_used ≤ 3.0 bo'lishi kerak.
    """
    await test_user_factory("sandbox_to@example.com", "testpass123")
    login = await client.post("/api/v1/auth/login", data={
        "username": "sandbox_to@example.com",
        "password": "testpass123",
    })
    token = login.json()["access_token"]

    response = await client.post(
        "/api/v1/tools/sandbox",
        json={"code": "print('hi')", "timeout_seconds": 60},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["actual_timeout_used"] <= 3.0, (
        f"Server timeout cheklovi ishlamadi! actual_timeout_used={data['actual_timeout_used']}"
    )


@pytest.mark.asyncio
async def test_sandbox_blocked_by_ast(client: AsyncClient, test_user_factory, mock_redis_ok):
    """Taqiqlangan modul importi → success=False, xavfsizlik xatosi."""
    await test_user_factory("sandbox_ast@example.com", "testpass123")
    login = await client.post("/api/v1/auth/login", data={
        "username": "sandbox_ast@example.com",
        "password": "testpass123",
    })
    token = login.json()["access_token"]

    response = await client.post(
        "/api/v1/tools/sandbox",
        json={"code": "import os; os.system('ls')", "timeout_seconds": 2.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "Xavfsizlik" in (data["error"] or "")


@pytest.mark.asyncio
async def test_sandbox_refresh_token_rejected(client: AsyncClient, test_user_factory):
    """
    Refresh token bilan /tools/sandbox'ga kirish → 401.
    Bu token_type xavfsizlik testining amaliy isboti.
    """
    await test_user_factory("sandbox_ref@example.com", "testpass123")
    login = await client.post("/api/v1/auth/login", data={
        "username": "sandbox_ref@example.com",
        "password": "testpass123",
    })
    refresh_token = login.json()["refresh_token"]

    response = await client.post(
        "/api/v1/tools/sandbox",
        json={"code": "print('x')", "timeout_seconds": 2.0},
        headers={"Authorization": f"Bearer {refresh_token}"},
    )
    assert response.status_code == 401, (
        f"Refresh token bilan kirish rad etilmadi! Actual: {response.status_code}"
    )
