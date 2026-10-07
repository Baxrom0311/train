"""
test_file_validator.py — file_validator.py uchun testlar.

Tekshiriladigan holatlar:
1. sanitize_filename — path-traversal himoyasi
2. check_extension — ruxsatsiz kengaytma
3. check_magic_bytes — noto'g'ri magic bytes
4. save_file_streamed — hajm limiti (oshsa faylni o'chiradi)
5. validate_and_save — to'liq pipeline
"""

import asyncio
import pytest
import tempfile
from pathlib import Path

from app.core.file_validator import (
    sanitize_filename,
    check_extension,
    check_magic_bytes,
    save_file_streamed,
    validate_and_save,
    MAGIC_BYTES,
)


# ===========================================================
# 1. sanitize_filename
# ===========================================================

class TestSanitizeFilename:

    def test_normal_filename(self):
        assert sanitize_filename("report.pdf") == "report.pdf"

    def test_path_traversal_slash(self):
        result = sanitize_filename("../../etc/passwd")
        assert ".." not in result
        assert "/" not in result

    def test_path_traversal_backslash(self):
        result = sanitize_filename("..\\windows\\system32\\cmd.exe")
        assert ".." not in result
        assert "\\" not in result

    def test_special_chars_removed(self):
        result = sanitize_filename("my file (1)!@#.pdf")
        # Faqat a-zA-Z0-9_.- qolishi kerak
        for ch in result:
            assert ch in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-"

    def test_empty_after_sanitize(self):
        result = sanitize_filename("!!!###")
        assert result  # Bo'sh bo'lmasligi kerak
        assert result == "upload"

    def test_preserves_extension(self):
        result = sanitize_filename("my_doc.xlsx")
        assert result.endswith(".xlsx")

    def test_nested_path(self):
        """Nested path — faqat basename qoladi."""
        result = sanitize_filename("/uploads/user/../../secret.pdf")
        assert "/" not in result


# ===========================================================
# 2. check_extension
# ===========================================================

class TestCheckExtension:

    @pytest.mark.parametrize("filename,expected_ext", [
        ("doc.pdf", "pdf"),
        ("image.png", "png"),
        ("photo.jpg", "jpg"),
        ("report.docx", "docx"),
        ("data.xlsx", "xlsx"),
        ("archive.zip", "zip"),
    ])
    def test_allowed_extensions(self, filename, expected_ext):
        assert check_extension(filename) == expected_ext

    @pytest.mark.parametrize("filename", [
        "script.py",
        "shell.sh",
        "virus.exe",
        "page.html",
        "config.json",
    ])
    def test_banned_extensions(self, filename):
        with pytest.raises(ValueError, match="Ruxsat etilmagan"):
            check_extension(filename)

    def test_no_extension(self):
        with pytest.raises(ValueError, match="kengaytma"):
            check_extension("noextension")


# ===========================================================
# 3. check_magic_bytes
# ===========================================================

class TestCheckMagicBytes:

    def test_pdf_correct(self):
        check_magic_bytes(b"%PDF-1.4 content...", "pdf")

    def test_png_correct(self):
        check_magic_bytes(b"\x89PNG\r\n\x1a\n...", "png")

    def test_jpg_correct(self):
        check_magic_bytes(b"\xff\xd8\xff\xe0...", "jpg")

    def test_docx_correct(self):
        check_magic_bytes(b"PK\x03\x04...", "docx")

    def test_xlsx_correct(self):
        check_magic_bytes(b"PK\x03\x04...", "xlsx")

    def test_pdf_wrong_magic(self):
        """PDF kengaytmali, lekin aslida boshqa fayl."""
        with pytest.raises(ValueError, match="magic bytes"):
            check_magic_bytes(b"\xff\xd8\xff fake pdf", "pdf")

    def test_png_with_pdf_content(self):
        with pytest.raises(ValueError, match="magic bytes"):
            check_magic_bytes(b"%PDF-1.4", "png")

    def test_empty_data(self):
        with pytest.raises(ValueError):
            check_magic_bytes(b"", "pdf")


# ===========================================================
# 4. save_file_streamed
# ===========================================================

async def _bytes_iter(chunks: list[bytes]):
    """Test uchun async bayt oqimi yaratuvchi."""
    for chunk in chunks:
        yield chunk


class TestSaveFileStreamed:

    @pytest.mark.asyncio
    async def test_normal_save(self, tmp_path):
        dest = tmp_path / "test.pdf"
        data = b"Hello World " * 100
        size = await save_file_streamed(_bytes_iter([data]), dest, max_size_mb=1.0)
        assert size == len(data)
        assert dest.exists()
        assert dest.read_bytes() == data

    @pytest.mark.asyncio
    async def test_size_limit_exceeded_deletes_file(self, tmp_path):
        """Hajm limiti oshganda fayl o'chirilishi kerak."""
        dest = tmp_path / "big.pdf"
        # 2MB ma'lumot, limit 1MB
        chunk = b"X" * (1024 * 1024)  # 1MB chunk
        chunks = [chunk, chunk]  # 2MB jami

        with pytest.raises(ValueError, match="hajmi"):
            await save_file_streamed(_bytes_iter(chunks), dest, max_size_mb=1.0)

        # Fayl o'chirilgan bo'lishi kerak
        assert not dest.exists(), "Hajm oshganda fayl o'chirilishi kerak"

    @pytest.mark.asyncio
    async def test_exactly_at_limit_passes(self, tmp_path):
        """Limit chegarasida yoki ichida — o'tadi."""
        dest = tmp_path / "ok.pdf"
        data = b"Y" * (512 * 1024)  # 0.5MB, limit 1MB
        size = await save_file_streamed(_bytes_iter([data]), dest, max_size_mb=1.0)
        assert size == len(data)
        assert dest.exists()

    @pytest.mark.asyncio
    async def test_chunked_save(self, tmp_path):
        """Ko'p chunk — to'g'ri yig'ilishi kerak."""
        dest = tmp_path / "chunked.pdf"
        chunks = [b"chunk1_", b"chunk2_", b"chunk3"]
        expected = b"chunk1_chunk2_chunk3"
        size = await save_file_streamed(_bytes_iter(chunks), dest, max_size_mb=1.0)
        assert size == len(expected)
        assert dest.read_bytes() == expected


# ===========================================================
# 5. validate_and_save (to'liq pipeline)
# ===========================================================

class TestValidateAndSave:

    @pytest.mark.asyncio
    async def test_valid_pdf(self, tmp_path):
        pdf_content = b"%PDF-1.4 " + b"A" * 100
        result = await validate_and_save(
            _bytes_iter([pdf_content]),
            "report.pdf",
            tmp_path,
        )
        assert result["ext"] == "pdf"
        assert (tmp_path / result["filename"]).exists()

    @pytest.mark.asyncio
    async def test_path_traversal_in_filename(self, tmp_path):
        pdf_content = b"%PDF-1.4 content"
        result = await validate_and_save(
            _bytes_iter([pdf_content]),
            "../../etc/passwd.pdf",
            tmp_path,
        )
        # Sanitize qilingan nom ichida '..' bo'lmasligi kerak
        assert ".." not in result["filename"]
        assert "/" not in result["filename"]

    @pytest.mark.asyncio
    async def test_wrong_extension(self, tmp_path):
        with pytest.raises(ValueError, match="Ruxsat etilmagan"):
            await validate_and_save(
                _bytes_iter([b"print('hack')"]),
                "malware.py",
                tmp_path,
            )

    @pytest.mark.asyncio
    async def test_magic_bytes_mismatch(self, tmp_path):
        """PDF kengaytmali, lekin tarkibi PDF emas."""
        with pytest.raises(ValueError, match="magic bytes"):
            await validate_and_save(
                _bytes_iter([b"NOT A PDF CONTENT"]),
                "fake.pdf",
                tmp_path,
            )

    @pytest.mark.asyncio
    async def test_size_limit_exceeded(self, tmp_path):
        pdf_header = b"%PDF-1.4 "
        large_content = b"A" * (2 * 1024 * 1024)  # 2MB
        with pytest.raises(ValueError, match="hajmi"):
            await validate_and_save(
                _bytes_iter([pdf_header + large_content]),
                "big.pdf",
                tmp_path,
                max_size_mb=1.0,
            )

    @pytest.mark.asyncio
    async def test_empty_file_rejected(self, tmp_path):
        with pytest.raises(ValueError, match="Bo'sh fayl"):
            await validate_and_save(
                _bytes_iter([]),
                "empty.pdf",
                tmp_path,
            )

    @pytest.mark.asyncio
    async def test_valid_png(self, tmp_path):
        png_content = b"\x89PNG\r\n\x1a\n" + b"B" * 50
        result = await validate_and_save(
            _bytes_iter([png_content]),
            "image.png",
            tmp_path,
        )
        assert result["ext"] == "png"
