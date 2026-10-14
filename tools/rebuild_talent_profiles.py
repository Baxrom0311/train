#!/usr/bin/env python3
"""
Nomzod profillarini (`talent_profiles`, CONTRACT.md §33) Run'lardan qayta hisoblash.

Odatda kerak emas — profil Run yakunlanganda, sertifikat bekor qilinganda va
ssenariy katalogi o'zgarganda o'zi yangilanadi (§33.2). Bazani qo'lda
tuzatgandan keyin yoki §10.1 qoidasi o'zgargan relizdan so'ng ishga tushiriladi.
Har qanday vaqtda xavfsiz: har guruh alohida tranzaksiyada, ishlab turgan
sayt bilan parallel (§33.2 qulfi).

Ishlatish (backend/ papkasidan, `.env` bilan):

    python ../tools/rebuild_talent_profiles.py
"""
import asyncio
import os
import sys

BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import select, union  # noqa: E402

from app.database import AsyncSessionLocal  # noqa: E402
from app.models.enums import RunStatus  # noqa: E402
from app.models.scenario import Run  # noqa: E402
from app.models.talent import TalentProfile  # noqa: E402
from app.talent.profile import refresh_profiles  # noqa: E402

BATCH = 200


async def rebuild() -> int:
    async with AsyncSessionLocal() as db:
        # profili bo'lishi mumkin bo'lganlar va hozir profili borlar (eskirgani o'chsin)
        user_ids = sorted((await db.execute(union(
            select(Run.user_id).where(Run.status == RunStatus.COMPLETED),
            select(TalentProfile.user_id),
        ))).scalars().all())
        for i in range(0, len(user_ids), BATCH):
            await refresh_profiles(db, user_ids[i:i + BATCH])
            await db.commit()
    return len(user_ids)


if __name__ == "__main__":
    count = asyncio.run(rebuild())
    print(f"Qayta hisoblandi: {count} foydalanuvchi.")
