#!/usr/bin/env python3
"""
Web Push uchun VAPID kalit juftligi (CONTRACT.md §22.2).

    python tools/gen_vapid_keys.py

Chiqishni serverdagi `.env`ga qo'ying. Kalitni almashtirsangiz, barcha
mavjud obunalar ishlamay qoladi (foydalanuvchilar push'ni qayta yoqadi).
Kalit `py_vapid` (pywebpush bog'liqligi) bilan yaratiladi — qo'lda crypto yo'q.
"""
import base64

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def generate() -> tuple[str, str]:
    """(ochiq kalit — 65 bayt uncompressed, maxfiy kalit — 32 bayt) base64url."""
    vapid = Vapid()
    vapid.generate_keys()
    public = vapid.public_key.public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint,
    )
    private = vapid.private_key.private_numbers().private_value.to_bytes(32, "big")
    return b64url(public), b64url(private)


if __name__ == "__main__":
    public, private = generate()
    print(f"VAPID_PUBLIC_KEY={public}")
    print(f"VAPID_PRIVATE_KEY={private}")
    print("VAPID_SUBJECT=mailto:admin@example.uz")
