import os
import uuid
import re
from fastapi import UploadFile, HTTPException
from app.config import settings

# Ruxsat etilgan Magic bytes sarlavhalari
MAGIC_NUMBERS = {
    "pdf": [b"%PDF"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "jpg": [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
    "xlsx": [b"PK\x03\x04"], # ZIP format (Office OpenXML)
    "docx": [b"PK\x03\x04"],
    "zip": [b"PK\x03\x04"],
    "json": [b"{", b"["],
    "txt": [],
    "py": [],
    "sql": []
}

def sanitize_filename(filename: str) -> str:
    """Fayl nomidagi xavfli belgilarni olib tashlash (Path Traversal himoyasi)"""
    clean_name = os.path.basename(filename)
    clean_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', clean_name)
    return clean_name

async def validate_and_save_upload(file: UploadFile) -> str:
    """
    Yuklanayotgan faylni qat'iy xavfsizlik tekshiruvidan o'tkazish va xavfsiz saqlash.
    """
    clean_filename = sanitize_filename(file.filename or "upload.bin")
    ext = clean_filename.split(".")[-1].lower() if "." in clean_filename else ""

    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Ruxsat etilmagan fayl turi (.{ext}). Faqat quyidagi formatlar mumkin: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )

    # 1. Fayl sarlavhasini (boshlang'ich 512 bayt) o'qib tekshirish
    header = await file.read(512)
    await file.seek(0)

    # 2. Magic bytes tekshiruvi (binary fayllar uchun)
    if ext in MAGIC_NUMBERS and MAGIC_NUMBERS[ext]:
        matched = any(header.startswith(magic) for magic in MAGIC_NUMBERS[ext])
        if not matched:
            raise HTTPException(
                status_code=400,
                detail=f"Fayl formati va uning haqiqiy tarkibi mos kelmadi (MIME/Magic header invalid: .{ext})"
            )

    # 3. Faylni xavfsiz unikal nom bilan chunklar orqali oqimda (stream) saqlash (RAM DoS himoyasi)
    safe_name = f"{uuid.uuid4().hex[:12]}_{clean_filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, safe_name)
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    total_bytes = 0
    chunk_size = 64 * 1024 # 64KB chunks

    try:
        with open(file_path, "wb") as f:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    f.close()
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    raise HTTPException(
                        status_code=400,
                        detail=f"Fayl hajmi ruxsat etilgan limitdan oshib ketdi (Maksimal: {settings.MAX_FILE_SIZE_MB}MB)"
                    )
                f.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Faylni saqlashda xatolik yuz berdi: {str(e)}")

    return f"/uploads/{safe_name}"
