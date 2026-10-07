"""scenario/clock.py — ish-daqiqa matematikasi (CONTRACT.md §9.2). DB kerak emas."""
from datetime import date, datetime, time, timezone

import pytest

from app.scenario.clock import TASHKENT, WorkCalendar, parse_hhmm

# 2026-10-05 — dushanba
MON, TUE, WED, THU, FRI, SAT = (date(2026, 10, d) for d in (5, 6, 7, 8, 9, 10))
NEXT_MON = date(2026, 10, 12)

CAL = WorkCalendar()


def tk(d: date, hh: int, mm: int = 0) -> datetime:
    return datetime(d.year, d.month, d.day, hh, mm, tzinfo=TASHKENT)


def local(t: datetime) -> tuple[date, time]:
    loc = t.astimezone(TASHKENT)
    return loc.date(), loc.time().replace(second=0, microsecond=0)


@pytest.mark.parametrize(
    "start, minutes, expected",
    [
        (tk(WED, 17, 30), 60, (THU, time(9, 30))),
        (tk(FRI, 17, 30), 60, (NEXT_MON, time(9, 30))),
        (tk(THU, 17, 0), 60, (THU, time(18, 0))),       # bo'lak oxiri o'sha kunda qoladi
        (tk(TUE, 12, 0), 60, (TUE, time(13, 0))),
        (tk(TUE, 12, 30), 60, (TUE, time(14, 30))),     # tushlik o'tkazib yuboriladi
        (tk(TUE, 13, 20), 30, (TUE, time(14, 30))),     # tushlik ichidan boshlash
        (tk(SAT, 11, 0), 30, (NEXT_MON, time(9, 30))),
        (tk(TUE, 7, 40), 20, (TUE, time(9, 20))),
        (tk(TUE, 19, 0), 15, (WED, time(9, 15))),
        (tk(MON, 10, 0), 1080, (WED, time(12, 0))),     # 18 ish soati
        (tk(MON, 9, 0), 480 * 5, (FRI, time(18, 0))),   # to'liq ish haftasi
        (tk(TUE, 18, 0), 0, (WED, time(9, 0))),          # 0 → normalize
        (tk(TUE, 10, 15), 0, (TUE, time(10, 15))),
    ],
)
def test_add_work_minutes(start, minutes, expected):
    result = CAL.add_work_minutes(start, minutes)
    assert result.tzinfo is not None and result.utcoffset().total_seconds() == 0
    assert local(result) == expected


def test_holiday_is_skipped():
    cal = WorkCalendar(holidays=frozenset({THU}))
    assert local(cal.add_work_minutes(tk(WED, 17, 50), 20)) == (FRI, time(9, 10))
    assert not cal.is_workday(THU)
    assert cal.next_workday(WED) == FRI


def test_consecutive_holidays_and_weekend():
    cal = WorkCalendar(holidays=frozenset({THU, FRI, NEXT_MON}))
    assert local(cal.add_work_minutes(tk(WED, 18, 0), 1)) == (date(2026, 10, 13), time(9, 1))


def test_utc_input_is_accepted():
    # 12:30 UTC = 17:30 Toshkent
    start = datetime(2026, 10, 7, 12, 30, tzinfo=timezone.utc)
    assert local(CAL.add_work_minutes(start, 60)) == (THU, time(9, 30))


def test_naive_datetime_rejected():
    with pytest.raises(ValueError):
        CAL.add_work_minutes(datetime(2026, 10, 7, 10, 0), 10)


def test_negative_minutes_rejected():
    with pytest.raises(ValueError):
        CAL.add_work_minutes(tk(MON, 10), -1)


@pytest.mark.parametrize(
    "a, b, expected",
    [
        (tk(MON, 9), tk(MON, 18), 480),
        (tk(MON, 12, 30), tk(MON, 14, 30), 60),
        (tk(FRI, 17), tk(NEXT_MON, 10), 120),
        (tk(MON, 10), tk(MON, 10), 0),
        (tk(MON, 11), tk(MON, 10), 0),
        (tk(SAT, 9), tk(SAT, 18), 0),
    ],
)
def test_work_minutes_between(a, b, expected):
    assert CAL.work_minutes_between(a, b) == expected


def test_work_minutes_between_is_inverse_of_add():
    start = tk(WED, 11, 47)
    for minutes in (0, 1, 73, 480, 999, 2400):
        end = CAL.add_work_minutes(start, minutes)
        assert CAL.work_minutes_between(start, end) == minutes


@pytest.mark.parametrize(
    "day, at, expected",
    [
        (1, "09:00", 0),
        (1, "09:30", 30),
        (1, "12:59", 239),
        (1, "14:00", 240),
        (1, "17:30", 450),
        (2, "09:00", 480),
        (3, "14:15", 480 * 2 + 255),
    ],
)
def test_node_offset(day, at, expected):
    assert CAL.node_offset(day, at) == expected


@pytest.mark.parametrize("at", ["08:59", "13:00", "13:30", "18:00", "21:00"])
def test_node_offset_rejects_non_work_time(at):
    with pytest.raises(ValueError):
        CAL.node_offset(1, at)


def test_schedule_on_time_start_matches_scenario_clock():
    start = tk(MON, 9)
    assert local(CAL.schedule(start, 1, "17:30")) == (MON, time(17, 30))
    assert local(CAL.schedule(start, 2, "14:00")) == (TUE, time(14, 0))


def test_start_after_never_lands_on_segment_end():
    assert local(CAL.start_after(tk(TUE, 12, 30), 30)) == (TUE, time(14, 0))
    assert local(CAL.start_after(tk(TUE, 17, 30), 30)) == (WED, time(9, 0))
    # dedlayn esa bo'lak oxirida qoladi
    assert local(CAL.add_work_minutes(tk(TUE, 12, 30), 30)) == (TUE, time(13, 0))


def test_schedule_late_start_shifts_timeline():
    # §9.2 misoli: 15:00 da boshlangan Run — 1-kun ertasi 15:00 da tugaydi
    start = tk(WED, 15)
    assert CAL.is_late_start(start)
    assert local(CAL.schedule(start, 1, "09:30")) == (WED, time(15, 30))
    assert local(CAL.schedule(start, 1, "17:30")) == (THU, time(14, 30))
    assert local(CAL.day_end(start)) == (THU, time(15, 0))


def test_start_outside_work_hours_is_not_late():
    assert not CAL.is_late_start(tk(TUE, 20))     # → chorshanba 09:00
    assert not CAL.is_late_start(tk(MON, 9))
    assert local(CAL.day_end(tk(MON, 9))) == (MON, time(18, 0))


def test_ends_at_adds_two_workdays():
    assert local(CAL.ends_at(tk(THU, 17, 30))) == (NEXT_MON, time(18, 0))
    assert local(CAL.ends_at(tk(MON, 18, 0))) == (WED, time(18, 0))


def test_parse_hhmm():
    assert parse_hhmm("09:05") == time(9, 5)
    for bad in ("9:05", "0905", "25:00", "aa:bb"):
        with pytest.raises(ValueError):
            parse_hhmm(bad)


def test_bad_segments_rejected():
    with pytest.raises(ValueError):
        WorkCalendar(segments=((time(14), time(13)),))
    with pytest.raises(ValueError):
        WorkCalendar(segments=((time(9), time(13)), (time(12), time(18))))
