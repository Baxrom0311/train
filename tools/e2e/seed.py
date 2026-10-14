#!/usr/bin/env python3
"""
E2E stek yordamchisi (CONTRACT.md §34.2). `tools/e2e/stack.sh` va Playwright
fixture'lari (`frontend/e2e/support/seed.ts`) chaqiradi; natija — stdout'da JSON.

    seed.py offset              soxta soat siljishi (soniya): keyingi ish kuni 09:00 Toshkent
    seed.py reset               e2e bazasi va Redis DB'sini tozalaydi (faqat `*_e2e` baza)
    seed.py company  --email E --password P --name N --company C
    seed.py student  --email E --password P --name N [--completed SLUG]
    seed.py errors              ochiq xato guruhlari (§32.3) — test oxirida bo'sh bo'lishi shart

Foydalanuvchilar ro'yxatdan o'tish va admin tasdiqlashi oqimining **natijasi**
holatida yoziladi (email tasdiqlangan, tashkilot tasdiqlangan) — bu oqimlarning
o'zi backend testlarida. `--completed` — tugallangan Run: dvigatel funksiyalari
(`create_run`, `advance_run`, `submit_answer`, `decide`) o'tgan ish kunidagi
vaqtlar bilan, ballar qo'yiladi va `write_final_report` (sertifikat, profil)
chaqiriladi — talaba profili real yo'l bilan paydo bo'ladi.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import date, datetime, time, timedelta, timezone
from urllib.parse import urlsplit

BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "backend")
sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import select, text  # noqa: E402

from app.config import settings  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.database import AsyncSessionLocal, engine  # noqa: E402
from app.models.billing import Company  # noqa: E402
from app.models.enums import AIEvalStatus, DefaultRole, OrgType, RunStatus, ScenarioVersionStatus  # noqa: E402
from app.models.monitoring import ErrorGroup  # noqa: E402
from app.models.rbac import Role  # noqa: E402
from app.models.scenario import Scenario, ScenarioVersion  # noqa: E402
from app.models.user import User  # noqa: E402
from app.scenario.clock import TASHKENT  # noqa: E402
from app.scenario.engine import Answer, advance_run, create_run, decide, submit_answer  # noqa: E402
from app.scenario.holidays import official_holidays  # noqa: E402
from app.scenario.reports import write_final_report  # noqa: E402

DAY_START = time(9, 0)


def _workday(d: date, holidays: dict[date, str]) -> bool:
    return d.weekday() < 5 and d not in holidays


def target_day(today: date) -> date:
    """`today`dan keyingi birinchi ish kuni (dam olish va rasmiy bayramlarsiz)."""
    holidays = official_holidays([today.year, today.year + 1])
    d = today + timedelta(days=1)
    while not _workday(d, holidays):
        d += timedelta(days=1)
    return d


def previous_workday(d: date) -> date:
    holidays = official_holidays([d.year - 1, d.year])
    d -= timedelta(days=1)
    while not _workday(d, holidays):
        d -= timedelta(days=1)
    return d


def cmd_offset(_: argparse.Namespace) -> dict:
    now = datetime.now(timezone.utc)
    target = datetime.combine(target_day(now.astimezone(TASHKENT).date()), DAY_START, TASHKENT)
    return {"offset_seconds": int((target - now).total_seconds()), "target": target.isoformat()}


async def cmd_reset(_: argparse.Namespace) -> dict:
    db_name = urlsplit(settings.DATABASE_URL).path.lstrip("/")
    if not db_name.endswith("_e2e"):
        raise SystemExit(f"reset faqat *_e2e bazada ishlaydi, berilgan: {db_name!r}")
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
    await engine.dispose()

    from app.core.redis_client import redis_client
    redis_db = int(urlsplit(settings.REDIS_URL).path.lstrip("/") or 0)
    if redis_db == 0:
        raise SystemExit("reset Redis'ning 0-bazasini tozalamaydi — REDIS_URL'da alohida DB bering (…/5)")
    await redis_client.flushdb()
    return {"database": db_name, "redis_db": redis_db}


async def _role(db, name: str) -> Role:
    role = (await db.execute(select(Role).where(Role.name == name))).scalars().first()
    if role is None:
        raise SystemExit(f"'{name}' roli yo'q — avval alembic upgrade head")
    return role


async def cmd_company(args: argparse.Namespace) -> dict:
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        company = Company(
            name=args.company, industry="IT", contact_email=args.email,
            is_verified=True, verified_at=now,
        )
        db.add(company)
        await db.flush()
        user = User(
            email=args.email, hashed_password=get_password_hash(args.password), full_name=args.name,
            role_id=(await _role(db, DefaultRole.COMPANY_HR.value)).id,
            org_type=OrgType.COMPANY, org_id=company.id, is_active=True, email_verified_at=now,
        )
        db.add(user)
        await db.commit()
        return {"user_id": str(user.id), "company_id": str(company.id)}


# Tugallangan kun: (vaqt, node, ball yoki qaror varianti). `test_scenario_content.py`
# dagi kuchli yo'l bilan bir xil — kontent o'zgarsa u test ham yiqiladi.
COMPLETED_PATHS: dict[str, list[tuple[str, str, int | str]]] = {
    "lazurit-go-backend-day1": [
        ("09:10", "standup", 80),
        ("10:30", "bug_promo", 90),
        ("11:35", "pm_request", "finish_bug"),
        ("14:30", "api_design", 70),
        ("15:50", "incident_orders", 75),
        ("17:40", "day1_end", 80),
    ],
}


async def _completed_run(db, user: User, slug: str, day: date) -> dict:
    steps = COMPLETED_PATHS.get(slug)
    if steps is None:
        raise SystemExit(f"--completed uchun yo'l yozilmagan: {slug} (bor: {', '.join(COMPLETED_PATHS)})")
    version = (await db.execute(
        select(ScenarioVersion).join(Scenario, ScenarioVersion.scenario_id == Scenario.id)
        .where(Scenario.slug == slug, ScenarioVersion.status == ScenarioVersionStatus.PUBLISHED)
    )).scalars().first()
    if version is None:
        raise SystemExit(f"{slug} nashr qilinmagan — import_scenario.py --publish")

    def at(hhmm: str) -> datetime:
        return datetime.combine(day, time.fromisoformat(hhmm), TASHKENT).astimezone(timezone.utc)

    start = at("09:00")
    run, _ = await create_run(db, user.id, version, start, start)
    await advance_run(db, run, start)
    for hhmm, node_id, value in steps:
        now = at(hhmm)
        await advance_run(db, run, now)
        if isinstance(value, str):
            await decide(db, run, node_id, value, now)
        else:
            sub, _ = await submit_answer(db, run, node_id, Answer(text="E2E: oldindan tayyorlangan javob."), now)
            sub.ai_eval_status = AIEvalStatus.COMPLETED
            sub.ai_score = value
            sub.ai_feedback = "Yaxshi bajarilgan."
        await db.flush()
    await db.commit()
    await db.refresh(run)
    if run.status != RunStatus.COMPLETED:
        raise SystemExit(f"Run tugallanmadi: {run.status}")
    if not await write_final_report(db, run.id, at("17:45")):
        raise SystemExit("yakuniy hisobot yozilmadi")
    return {"run_id": str(run.id)}


async def cmd_student(args: argparse.Namespace) -> dict:
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        user = User(
            email=args.email, hashed_password=get_password_hash(args.password), full_name=args.name,
            role_id=(await _role(db, DefaultRole.STUDENT.value)).id, is_active=True, email_verified_at=now,
        )
        db.add(user)
        await db.commit()
        out: dict = {"user_id": str(user.id)}
        if args.completed:
            day = previous_workday(now.astimezone(TASHKENT).date())
            out |= await _completed_run(db, user, args.completed, day)
        return out


async def cmd_errors(_: argparse.Namespace) -> dict:
    async with AsyncSessionLocal() as db:
        groups = (await db.execute(
            select(ErrorGroup).where(ErrorGroup.status == "open").order_by(ErrorGroup.last_seen)
        )).scalars().all()
        return {"errors": [
            {"source": g.source, "title": g.title, "location": g.location, "count": g.count} for g in groups
        ]}


def main() -> None:
    parser = argparse.ArgumentParser(description="TryJob e2e seed (CONTRACT.md §34.2)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("offset")
    sub.add_parser("reset")
    sub.add_parser("errors")
    for name in ("company", "student"):
        p = sub.add_parser(name)
        p.add_argument("--email", required=True)
        p.add_argument("--password", required=True)
        p.add_argument("--name", required=True)
        if name == "company":
            p.add_argument("--company", required=True)
        else:
            p.add_argument("--completed", metavar="SLUG")
    args = parser.parse_args()

    if args.cmd == "offset":
        result = cmd_offset(args)
    else:
        handler = {
            "reset": cmd_reset, "company": cmd_company, "student": cmd_student, "errors": cmd_errors,
        }[args.cmd]

        async def run() -> dict:
            try:
                return await handler(args)
            finally:
                await engine.dispose()

        result = asyncio.run(run())
    print(json.dumps(result))


if __name__ == "__main__":
    main()
