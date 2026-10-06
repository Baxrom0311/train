import pytest
from app.core.file_validator import sanitize_filename

def test_sanitize_filename_prevents_path_traversal():
    dangerous_names = [
        "../../etc/passwd",
        "../../../malicious.py",
        "nested/folder/file.xlsx",
        "evil\\win32\\system.dll"
    ]
    for name in dangerous_names:
        cleaned = sanitize_filename(name)
        assert "/" not in cleaned
        assert "\\" not in cleaned
        assert ".." not in cleaned
