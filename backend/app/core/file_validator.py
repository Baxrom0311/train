"""
file_validator.py — Fayl yuklash xavfsizligi.

Imkoniyatlar:
- Magic bytes tekshiruvi (fayl kengaytmasiga emas, tarkibiga qarab)
- sanitize_filename: path-traversal himoyasi
- Streamed saqlash: MAX_FILE_SIZE_MB oshsa — to'xtatib, faylni o'chiradi
"""

import os
import re
import asyncio
import aiofiles
from pathlib import Path
from typing import AsyncIterator

# Magic bytes mapping: fayl turi → kutilayotgan boshlang'ich baytlar
MAGIC_BYTES: dict[str, bytes] = {
    "pdf":  b"%PDF",
    "png":  b"\x89PNG",
    "jpg":  b"\xff\xd8\xff",
    "docx": b"PK\x03\x04",  # ZIP-asosida (docx, xlsx ham shu)
    "xlsx": b"PK\x03\x04",
    "zip":  b"PK\x03\x04",
}

# Ruxsat etilgan kengaytmalar
ALLOWED_EXTENSIONS = frozenset(MAGIC_BYTES.keys())

# Maksimal fayl hajmi (MB)
MAX_FILE_SIZE_MB: float = 10.0

# Fayl nomida faqat quyidagi belgilarga ruxsat
_SAFE_FILENAME_RE = re.compile(r"[^a-zA-Z0-9_.\-]")


def sanitize_filename(filename: str) -> str:
    """
    Path-traversal himoyasi:
    - Barcha '/' va '\\' va '..' ni olib tashlaydi.
    - Faqat a-zA-Z0-9_.- belgilarni qoldiradi.
    - Bo'sh yoki xavfli natijada fallback nomini qaytaradi.
    """
    # Path komponentini ajratib olamiz (oxirgi qism)
    basename = Path(filename).name
    # Maxsus belgilarni "_" bilan almashtirish
    safe = _SAFE_FILENAME_RE.sub("_", basename)
    # Boshidagi nuqta va chiziqchalarni olib tashlash
    safe = safe.lstrip(".-_")
    if not safe:
        safe = "upload"
    return safe


def check_extension(filename: str) -> str:
    """
    Fayl kengaytmasini tekshiradi.
    Ruxsat etilmagan kengaytmada ValueError ko'taradi.
    Kengaytmani (kichik harfda) qaytaradi.
    """
    parts = filename.rsplit(".", 1)
    if len(parts) < 2:
        raise ValueError("Fayl kengaytmasi yo'q")
    ext = parts[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Ruxsat etilmagan fayl turi: .{ext}")
    return ext


def check_magic_bytes(data: bytes, ext: str) -> None:
    """
    Fayl boshlang'ich baytlarini kutilgan magic bytes bilan solishtiradi.
    Mos kelmasa — ValueError ko'taradi.
    """
    expected = MAGIC_BYTES.get(ext)
    if expected is None:
        raise ValueError(f"Magic bytes noma'lum kengaytma uchun: {ext}")
    if not data.startswith(expected):
        raise ValueError(
            f"Fayl tarkibi .{ext} formatiga mos kelmaydi (magic bytes xato)"
        )


async def save_file_streamed(
    upload_iterator: AsyncIterator[bytes],
    destination: Path,
    max_size_mb: float = MAX_FILE_SIZE_MB,
) -> int:
    """
    Faylni chunk-chunk (oqim) bilan saqlaydi.
    Hajm MAX_FILE_SIZE_MB'dan oshsa — faylni o'chirib, ValueError ko'taradi.

    :param upload_iterator: AsyncIterator[bytes] — fayl tarkibi oqimi
    :param destination: Saqlanadigan yo'l
    :param max_size_mb: Maksimal hajm (MB)
    :returns: Saqlangan baytlar soni
    """
    max_bytes = int(max_size_mb * 1024 * 1024)
    total = 0
    destination.parent.mkdir(parents=True, exist_ok=True)

    try:
        async with aiofiles.open(destination, "wb") as f:
            async for chunk in upload_iterator:
                total += len(chunk)
                if total > max_bytes:
                    # Limitni oshirdi — darhol to'xtating va faylni o'chirish
                    await f.flush()
                    raise ValueError(
                        f"Fayl hajmi {max_size_mb}MB dan oshdi. Yuklash bekor qilindi."
                    )
                await f.write(chunk)
    except ValueError:
        # Yarim saqlangan faylni o'chiramiz
        if destination.exists():
            destination.unlink()
        raise

    return total


async def validate_and_save(
    upload_iterator: AsyncIterator[bytes],
    original_filename: str,
    destination_dir: Path,
    max_size_mb: float = MAX_FILE_SIZE_MB,
) -> dict:
    """
    To'liq validatsiya va saqlash pipeline:
    1. Kengaytma tekshiruvi
    2. Dastlabki chunk dan magic bytes tekshiruvi
    3. Streamed saqlash (hajm limiti bilan)

    :returns: {"filename": str, "size_bytes": int, "ext": str}
    """
    # 1. Kengaytma
    ext = check_extension(original_filename)
    safe_name = sanitize_filename(original_filename)
    dest = destination_dir / safe_name

    # Magic bytes uchun dastlabki chunk kerak — iterator'ni "peek" qilamiz
    first_chunk: bytes = b""
    chunks_buffer = []

    async def _buffered():
        nonlocal first_chunk
        yielded_first = False
        async for chunk in upload_iterator:
            if not yielded_first:
                first_chunk = chunk
                yielded_first = True
            chunks_buffer.append(chunk)
            yield chunk

    buffered_iter = _buffered()

    # Birinchi chunk'ni olish uchun bir marta next qilamiz
    try:
        first = await buffered_iter.__anext__()
    except StopAsyncIteration:
        raise ValueError("Bo'sh fayl yuborildi")

    # 2. Magic bytes tekshiruvi
    check_magic_bytes(first, ext)

    # Birinchi chunkni va qolganlarini birlashtirgan yangi iterator
    async def _with_first():
        yield first
        async for chunk in buffered_iter:
            yield chunk

    # 3. Streamed saqlash
    size = await save_file_streamed(_with_first(), dest, max_size_mb)

    return {"filename": safe_name, "size_bytes": size, "ext": ext}
