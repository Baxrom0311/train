"""
Ish vaqti kalendari va ish-daqiqa matematikasi (CONTRACT.md §9.2).

Barcha vaqt hisoblari shu modulda: DB'ga, `datetime.now()`ga va boshqa
modullarga bog'liq emas — `now` har doim parametr sifatida uzatiladi.

Ish vaqti: dushanba–juma, 09:00–13:00 va 14:00–18:00 (Asia/Tashkent),
`holidays`dagi sanalar ish kuni emas. Kirish vaqtlari timezone'li
(aware) bo'lishi shart; natijalar UTC'da qaytariladi (DB `timestamptz`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

TASHKENT = ZoneInfo("Asia/Tashkent")

# (boshlanish, tugash) — yarim ochiq [start, end) oraliqlar, vaqt tartibida.
DEFAULT_SEGMENTS: tuple[tuple[time, time], ...] = (
    (time(9, 0), time(13, 0)),
    (time(14, 0), time(18, 0)),
)

# Bayramlar ketma-ket kelishi mumkin, lekin bir yilda ish kuni topilmasligi
# — kalendar noto'g'ri to'ldirilgani belgisi.
_MAX_DAYS_SCAN = 366


def parse_hhmm(value: str) -> time:
    """`"09:30"` → `time(9, 30)`. Noto'g'ri format → ValueError."""
    try:
        hh, mm = value.split(":")
        if len(hh) != 2 or len(mm) != 2:
            raise ValueError
        return time(int(hh), int(mm))
    except ValueError:
        raise ValueError(f"vaqt 'HH:MM' formatida bo'lishi kerak: {value!r}") from None


def _require_aware(t: datetime) -> None:
    if t.tzinfo is None or t.utcoffset() is None:
        raise ValueError("timezone'siz (naive) datetime qabul qilinmaydi")


def _minutes(td: timedelta) -> float:
    return td.total_seconds() / 60


@dataclass(frozen=True)
class WorkCalendar:
    tz: ZoneInfo = TASHKENT
    segments: tuple[tuple[time, time], ...] = DEFAULT_SEGMENTS
    holidays: frozenset[date] = frozenset()

    def __post_init__(self) -> None:
        prev_end: time | None = None
        for start, end in self.segments:
            if start >= end or (prev_end is not None and start < prev_end):
                raise ValueError("ish bo'laklari tartibli va kesishmaydigan bo'lishi kerak")
            prev_end = end
        if not self.segments:
            raise ValueError("kamida bitta ish bo'lagi kerak")

    # ── Kunlar ────────────────────────────────────────────────────────

    @property
    def minutes_per_day(self) -> int:
        return sum(
            (end.hour * 60 + end.minute) - (start.hour * 60 + start.minute)
            for start, end in self.segments
        )

    def is_workday(self, d: date) -> bool:
        return d.weekday() < 5 and d not in self.holidays

    def next_workday(self, d: date) -> date:
        """`d`dan **keyingi** birinchi ish kuni (`d`ning o'zi hisobga olinmaydi)."""
        for _ in range(_MAX_DAYS_SCAN):
            d += timedelta(days=1)
            if self.is_workday(d):
                return d
        raise ValueError("bir yil ichida ish kuni topilmadi — bayramlar ro'yxatini tekshiring")

    def _bounds(self, d: date) -> list[tuple[datetime, datetime]]:
        return [
            (datetime.combine(d, start, self.tz), datetime.combine(d, end, self.tz))
            for start, end in self.segments
        ]

    def is_work_time(self, value: time) -> bool:
        """Kun ichidagi vaqt ish bo'lagiga tushadimi (tushlik va 18:00 — yo'q)."""
        return any(start <= value < end for start, end in self.segments)

    # ── Normallashtirish va qo'shish ─────────────────────────────────

    def normalize(self, t: datetime) -> datetime:
        """
        `t` ish vaqti ichida bo'lsa — o'zi, aks holda keyingi ish bo'lagining
        boshi. Bo'lak oxiri (13:00, 18:00) ham keyingi bo'lak boshiga suriladi.
        """
        _require_aware(t)
        local = t.astimezone(self.tz)
        d = local.date()
        for _ in range(_MAX_DAYS_SCAN):
            if self.is_workday(d):
                for start, end in self._bounds(d):
                    if local < end:
                        return max(local, start).astimezone(timezone.utc)
            d += timedelta(days=1)
            local = datetime.combine(d, time.min, self.tz)
        raise ValueError("bir yil ichida ish vaqti topilmadi — bayramlar ro'yxatini tekshiring")

    def add_work_minutes(self, t: datetime, minutes: int) -> datetime:
        """
        `t`ga `minutes` ish daqiqasi qo'shadi: tushlik, kechqurun, dam olish
        va bayram kunlari o'tkazib yuboriladi. Natija bo'lak oxiriga aynan
        tushsa (13:00, 18:00) — o'sha vaqt qaytadi, keyingi bo'lak emas.
        """
        if minutes < 0:
            raise ValueError("minutes manfiy bo'lishi mumkin emas")
        cur = self.normalize(t).astimezone(self.tz)
        remaining = timedelta(minutes=minutes)
        if not remaining:
            return cur.astimezone(timezone.utc)
        while True:
            seg_end = next(end for start, end in self._bounds(cur.date()) if start <= cur < end)
            available = seg_end - cur
            if remaining <= available:
                return (cur + remaining).astimezone(timezone.utc)
            remaining -= available
            cur = self.normalize(seg_end).astimezone(self.tz)

    def work_minutes_between(self, a: datetime, b: datetime) -> int:
        """`[a, b)` oralig'idagi ish daqiqalari (butun qismi). `b <= a` → 0."""
        _require_aware(a)
        _require_aware(b)
        if b <= a:
            return 0
        a_loc, b_loc = a.astimezone(self.tz), b.astimezone(self.tz)
        total = timedelta()
        d = a_loc.date()
        while d <= b_loc.date():
            if self.is_workday(d):
                for start, end in self._bounds(d):
                    lo, hi = max(start, a_loc), min(end, b_loc)
                    if hi > lo:
                        total += hi - lo
            d += timedelta(days=1)
        return int(_minutes(total))

    # ── Ssenariy vaqt jadvali (§9.2) ─────────────────────────────────

    def node_offset(self, day: int, at: str) -> int:
        """
        Ssenariydagi `day` + `at` → Run boshidan ish-daqiqa siljishi:
        `(day-1) · minutes_per_day + 09:00 → at` oralig'idagi ish daqiqalari.
        """
        if day < 1:
            raise ValueError("day 1 dan boshlanadi")
        at_time = parse_hhmm(at)
        if not self.is_work_time(at_time):
            raise ValueError(f"{at} ish vaqtiga tushmaydi")
        within = 0
        at_min = at_time.hour * 60 + at_time.minute
        for start, end in self.segments:
            s, e = start.hour * 60 + start.minute, end.hour * 60 + end.minute
            within += max(0, min(e, at_min) - s)
        return (day - 1) * self.minutes_per_day + within

    def start_after(self, t: datetime, minutes: int) -> datetime:
        """
        Hodisa **boshlanish** vaqti: `add_work_minutes` + `normalize`. Dedlayn
        bo'lak oxirida (13:00) tugashi mumkin, lekin yangi hodisa tushlikda
        yoki 18:00 da kelmaydi — keyingi bo'lak boshiga suriladi. Nisbiy
        (`after`) node'lar ham shu bilan rejalashtiriladi.
        """
        return self.normalize(self.add_work_minutes(t, minutes))

    def schedule(self, start_at: datetime, day: int, at: str) -> datetime:
        """Fixed node'ning haqiqiy vaqti: `start_at` + `node_offset`."""
        return self.start_after(start_at, self.node_offset(day, at))

    def day_end(self, start_at: datetime, day: int = 1) -> datetime:
        """Run'ning `day`-kuni haqiqatda qachon tugashi (kech boshlangan Run uchun ogohlantirish)."""
        return self.add_work_minutes(start_at, day * self.minutes_per_day)

    def is_late_start(self, start_at: datetime) -> bool:
        """`start_at` ish kunining birinchi bo'lagi boshidan kech bo'lsa — True."""
        local = self.normalize(start_at).astimezone(self.tz)
        return local.time() != self.segments[0][0]

    def ends_at(self, last_scheduled_at: datetime, grace_workdays: int = 2) -> datetime:
        """
        Run'ning yonish chegarasi (§9.2): eng kech fixed node kunidan keyingi
        `grace_workdays`-ish kunining oxirgi bo'lagi tugashi.
        """
        _require_aware(last_scheduled_at)
        d = last_scheduled_at.astimezone(self.tz).date()
        for _ in range(grace_workdays):
            d = self.next_workday(d)
        return datetime.combine(d, self.segments[-1][1], self.tz).astimezone(timezone.utc)
