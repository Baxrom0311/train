"""
Bayramlar: `work_holidays` jadvali ↔ `WorkCalendar` (CONTRACT.md §9.2, Q8).

- `load_calendar(db)` — dvigatel va API shu kalendardan foydalanadi.
- `sync_work_holidays(db, today)` — `holidays` paketining O'zbekiston
  kalendaridan joriy va keyingi yil sanalarini `source=auto` sifatida yozadi,
  lekin faqat hali bitta ham `auto` yozuvi yo'q yil uchun. Shunday qilib
  admin tuzatishi (taxminiy hayit sanasini o'chirish, `manual` qo'shish)
  keyingi sinxronizatsiyada qaytib kelmaydi.
"""

from datetime import date

import holidays as holidays_pkg
from sqlalchemy import extract, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import HolidaySource
from app.models.scenario import WorkHoliday
from app.scenario.clock import WorkCalendar


async def load_calendar(db: AsyncSession) -> WorkCalendar:
    dates = (await db.execute(select(WorkHoliday.date))).scalars().all()
    return WorkCalendar(holidays=frozenset(dates))


def official_holidays(years: list[int]) -> dict[date, str]:
    return dict(holidays_pkg.country_holidays("UZ", years=years, language="uz"))


async def sync_work_holidays(db: AsyncSession, today: date) -> int:
    """Yozilgan `auto` sanalar sonini qaytaradi. Commit chaqiruvchida."""
    synced_years = {int(y) for y in (await db.execute(
        select(extract("year", WorkHoliday.date)).where(WorkHoliday.source == HolidaySource.AUTO).distinct()
    )).scalars().all()}
    years = [y for y in (today.year, today.year + 1) if y not in synced_years]
    if not years:
        return 0
    rows = [
        {"date": d, "name": name[:200], "source": HolidaySource.AUTO}
        for d, name in official_holidays(years).items()
    ]
    if not rows:
        return 0
    # `manual` yozuv bor sanaga tegilmaydi
    result = await db.execute(insert(WorkHoliday).values(rows).on_conflict_do_nothing(index_elements=["date"]))
    return result.rowcount or 0
