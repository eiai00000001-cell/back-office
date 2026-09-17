"""app/utils/date_range.py のテスト。詳細設計書4.8.1章・3.8章(SC-08初期表示期間)。"""
from datetime import date

from app.utils.date_range import build_last_12_months, month_end, month_start


class TestBuildLast12Months:
    def test_returns_12_months_ending_with_base_month(self):
        result = build_last_12_months(date(2026, 9, 17))
        assert result == [
            "2025-10",
            "2025-11",
            "2025-12",
            "2026-01",
            "2026-02",
            "2026-03",
            "2026-04",
            "2026-05",
            "2026-06",
            "2026-07",
            "2026-08",
            "2026-09",
        ]

    def test_handles_year_boundary_crossing_at_start_of_year(self):
        result = build_last_12_months(date(2026, 1, 5))
        assert result[0] == "2025-02"
        assert result[-1] == "2026-01"
        assert len(result) == 12

    def test_ascending_order(self):
        result = build_last_12_months(date(2026, 3, 1))
        assert result == sorted(result)


class TestMonthStart:
    def test_returns_first_day_of_month(self):
        assert month_start("2026-09") == "2026-09-01"


class TestMonthEnd:
    def test_returns_last_day_of_31_day_month(self):
        assert month_end(date(2026, 9, 17)) == "2026-09-30"

    def test_returns_last_day_of_february_in_leap_year(self):
        assert month_end(date(2028, 2, 10)) == "2028-02-29"

    def test_returns_last_day_of_february_in_non_leap_year(self):
        assert month_end(date(2026, 2, 10)) == "2026-02-28"
