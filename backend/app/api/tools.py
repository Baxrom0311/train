"""
tools.py — POST /tools/sandbox endpoint.

Xavfsizlik talablari (CONTRACT.md §4, task 02 §4):
- MAJBURIY auth: current_user = Depends(get_current_user)
- Redis rate-limit: foydalanuvchiga daqiqasiga 10 ta so'rov
- timeout_seconds: client qiymatiga ishonilmaydi — server min(val, 3.0) bilan cheklaydi
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional

from app.core.deps import get_current_user, rate_limit
from app.core.sandbox import run_code, SandboxResult
from app.models.user import User

router = APIRouter(prefix="/tools", tags=["tools"])


class PythonRunRequest(BaseModel):
    code: str = Field(..., description="Bajariladigan Python kodi")
    timeout_seconds: Optional[float] = Field(
        default=2.0,
        ge=0.1,
        le=60.0,  # Pydantic validatsiya (lekin server baribir min() qo'llaydi)
        description="Timeout sekund (server max 3.0s ga qisqartiradi)",
    )


class SandboxResponse(BaseModel):
    success: bool
    stdout: str
    stderr: str
    error: Optional[str] = None
    actual_timeout_used: float


@router.post(
    "/sandbox",
    response_model=SandboxResponse,
    summary="Python kodini xavfsiz sandbox'da bajar",
    description=(
        "Auth talab qilinadi. "
        "Rate-limit: daqiqasiga 10 ta so'rov. "
        "timeout_seconds qiymati server tomonidan 3.0s dan oshmaslikka cheklanadi."
    ),
)
async def run_python_code(
    data: PythonRunRequest,
    current_user: User = Depends(get_current_user),           # MAJBURIY auth
    _rl: User = Depends(rate_limit("sandbox", max_requests=10, window_seconds=60, fail_closed=True)),
):
    # Server tomonidan qattiq cheklov — client timeout_seconds qiymatiga ishonilmaydi
    timeout = min(data.timeout_seconds or 2.0, 3.0)

    result: SandboxResult = run_code(data.code, timeout=timeout)

    return SandboxResponse(
        success=result.success,
        stdout=result.stdout,
        stderr=result.stderr,
        error=result.error,
        actual_timeout_used=timeout,
    )
