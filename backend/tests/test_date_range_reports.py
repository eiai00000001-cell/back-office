"""build_month_keys / add_years / 期間変換(詳細設計書4.10.5・4.11.1・4.12.1章)。"""
from datetime import date

import pytest

from app.utils.date_range import add_years, build_month_keys, period_to_dates


def test_build_month_keys_inclusive_across_year():
    assert build_month_keys("2025-11-01", "2026-02-28") == ["2025-11", "2025-12", "2026-01", "2026-02"]


def test_build_month_keys_single_month():
    assert build_month_keys("2026-09-01", "2026-09-30") == ["2026-09"]


def test_add_years_keeps_month_and_day():
    assert add_years(date(2026, 3, 15), 1) == date(2027, 3, 15)


def test_add_years_leap_day_to_non_leap_year():
    assert add_years(date(2028, 2, 29), 1) == date(2029, 2, 28)
    assert add_years(date(2028, 2, 29), 4) == date(2032, 2, 29)


@pytest.mark.parametrize(
    "start,end,expected",
    [("2025-10", "2026-09", ("2025-10-01", "2026-09-30")), ("2028-02", "2028-02", ("2028-02-01", "2028-02-29"))],
)
def test_period_to_dates(start, end, expected):
    assert period_to_dates(start, end) == expected
