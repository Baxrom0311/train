#!/usr/bin/env python3
"""
Birinchi `admin` foydalanuvchini yaratish uchun CLI skript.

Nega kerak: ro'yxatdan o'tish (`/auth/register`, `/auth/register-org`) orqali
faqat `student`, `company_hr`, `university_admin` yaratiladi — ularning
oxirgisi ikkisi admin tasdiqlovini kutadi. Demak birinchi admin akkaunti
tizim ichida HECH QACHON o'z-o'zidan paydo bo'lmaydi — buni faqat shu skript
(server tomoni, deploy paytida bir marta) yaratishi kerak.

Ishlatish (backend/ papkasidan, virtualenv faollashtirilgan holda):

    python ../tools/bootstrap_admin.py --email admin@tryjob.uz --password "KuchliParol123!"

Yoki muhit o'zgaruvchilari orqali (masalan deploy skriptida):

    ADMIN_EMAIL=admin@tryjob.uz ADMIN_PASSWORD=... python ../tools/bootstrap_admin.py

Talab: `alembic upgrade head` avval ishga tushirilgan bo'lishi kerak
(roles/permissions seed qilingan bo'lishi shart — CONTRACT.md §4).
"""
import argparse
import asyncio
import os
import sys

BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
sys.path.insert(0, BACKEND_DIR)

from sqlalchemy.future import select  # noqa: E402

from app.database import AsyncSessionLocal  # noqa: E402
from app.models.rbac import Role  # noqa: E402
from app.models.user import User  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402


async def create_admin(email: str, password: str, full_name: str) -> None:
    async with AsyncSessionLocal() as session:
        existing = await session.execute(select(User).where(User.email == email))
        if existing.scalars().first():
            print(f"Xato: '{email}' bilan foydalanuvchi allaqachon mavjud.")
            sys.exit(1)

        role_result = await session.execute(select(Role).where(Role.name == "admin"))
        admin_role = role_result.scalars().first()
        if not admin_role:
            print(
                "Xato: 'admin' roli bazada topilmadi. Avval migratsiyalarni"
                " ishga tushiring: alembic upgrade head"
            )
            sys.exit(1)

        user = User(
            email=email,
            hashed_password=get_password_hash(password),
            full_name=full_name,
            role_id=admin_role.id,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        print(f"Admin foydalanuvchi yaratildi: {email}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Birinchi admin akkauntini yaratish")
    parser.add_argument("--email", default=os.getenv("ADMIN_EMAIL"))
    parser.add_argument("--password", default=os.getenv("ADMIN_PASSWORD"))
    parser.add_argument(
        "--full-name", default=os.getenv("ADMIN_FULL_NAME", "Platform Admin")
    )
    args = parser.parse_args()

    if not args.email or not args.password:
        parser.error(
            "--email va --password shart (yoki ADMIN_EMAIL / ADMIN_PASSWORD "
            "muhit o'zgaruvchilari orqali bering)."
        )

    asyncio.run(create_admin(args.email, args.password, args.full_name))


if __name__ == "__main__":
    main()
