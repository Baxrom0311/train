"""
Run fayllari (CONTRACT.md §9.5, §9.9). Fayllar nginx orqali to'g'ridan-to'g'ri
berilmaydi — faqat shu auth'li endpoint orqali: egasi yoki
`manage_simulations` ruxsati bor foydalanuvchi (admin). Boshqalarga 404.
"""

import hashlib
import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.deps import get_current_active_user, rate_limit
from app.core.file_validator import validate_and_save
from app.database import get_db
from app.models.scenario import Run, UploadedFile
from app.models.user import User

router = APIRouter(tags=["files"])

# Egasidan boshqa kim ko'ra oladi (RBAC — §4, inline rol tekshiruvi yo'q)
VIEW_PERMISSION = "manage_simulations"
READ_CHUNK = 64 * 1024
MIME = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "zip": "application/zip",
}


class FileOut(BaseModel):
    id: uuid.UUID
    original_name: str
    mime: str
    size_bytes: int
    run_id: uuid.UUID | None


def _upload_dir() -> Path:
    return Path(settings.UPLOAD_DIR)


async def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    async with aiofiles.open(path, "rb") as f:
        while chunk := await f.read(READ_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def _can_view(user: User, f: UploadedFile) -> bool:
    if f.owner_user_id == user.id:
        return True
    role = user.role
    return bool(role and any(p.key == VIEW_PERMISSION for p in role.permissions))


@router.post("/files", response_model=FileOut, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    run_id: uuid.UUID | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(rate_limit("file_upload", max_requests=20, window_seconds=60)),
):
    if run_id is not None:
        run = await db.get(Run, run_id)
        if run is None or run.user_id != user.id:
            raise HTTPException(status_code=404, detail="Run topilmadi")

    async def chunks():
        while chunk := await file.read(READ_CHUNK):
            yield chunk

    original = (file.filename or "upload").strip()[:255]
    try:
        saved = await validate_and_save(chunks(), original, _upload_dir())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    path = _upload_dir() / saved["filename"]
    record = UploadedFile(
        owner_user_id=user.id,
        run_id=run_id,
        stored_path=saved["filename"],          # UPLOAD_DIR'ga nisbatan
        original_name=original,
        mime=MIME.get(saved["ext"], "application/octet-stream"),
        size_bytes=saved["size_bytes"],
        sha256=await _sha256(path),
    )
    db.add(record)
    await db.commit()
    return FileOut(
        id=record.id, original_name=record.original_name, mime=record.mime,
        size_bytes=record.size_bytes, run_id=record.run_id,
    )


@router.get("/files/{file_id}")
async def download_file(
    file_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    f = await db.get(UploadedFile, file_id)
    if f is None or not _can_view(user, f):
        raise HTTPException(status_code=404, detail="Fayl topilmadi")
    root = _upload_dir().resolve()
    path = (root / f.stored_path).resolve()
    if root not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="Fayl topilmadi")
    return FileResponse(path, media_type=f.mime, filename=f.original_name)
