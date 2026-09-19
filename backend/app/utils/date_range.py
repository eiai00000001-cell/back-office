"""直近12ヶ月の期間算出ユーティリティ。詳細設計書4.8.1章・5.2章。

F-07(財務ダッシュボード)の対象期間算出と、SC-08(経費集計画面)の初期表示期間
「当月を含む直近12か月」(詳細設計書3.8章)とで算出方法を共通化する。
"""
import calendar
from datetime import date


def build_last_12_months(base_date: date) -> list[str]:
    """base_dateが属する月を含む、直近12ヶ月分の年月キー(YYYY-MM)を昇順で返す。"""
    total_months = base_date.year * 12 + (base_date.month - 1)
    months: list[str] = []
    for offset in range(11, -1, -1):
        target = total_months - offset
        year, month = divmod(target, 12)
        months.append(f"{year:04d}-{month + 1:02d}")
    return months


def month_start(month_key: str) -> str:
    """年月キー(YYYY-MM)から、その月の1日(YYYY-MM-01)を返す。"""
    return f"{month_key}-01"


def month_end(base_date: date) -> str:
    """base_dateが属する月の末日(YYYY-MM-DD)を返す。"""
    last_day = calendar.monthrange(base_date.year, base_date.month)[1]
    return base_date.replace(day=last_day).isoformat()


def build_month_keys(date_from: str, date_to: str) -> list[str]:
    """date_from〜date_to(YYYY-MM-DD)が含む年月キー(YYYY-MM)を昇順で返す(詳細設計書4.12.1)。"""
    start = date.fromisoformat(date_from)
    end = date.fromisoformat(date_to)
    total_start = start.year * 12 + (start.month - 1)
    total_end = end.year * 12 + (end.month - 1)
    keys = []
    for total in range(total_start, total_end + 1):
        year, month = divmod(total, 12)
        keys.append(f"{year:04d}-{month + 1:02d}")
    return keys


def add_years(d: date, years: int) -> date:
    """同じ月日のyears年後を返す。2月29日で対象年が平年の場合は2月28日とする(詳細設計書4.10.5)。"""
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        return d.replace(year=d.year + years, day=28)


def period_to_dates(period_from: str, period_to: str) -> tuple[str, str]:
    """年月(YYYY-MM)の範囲を、開始月の月初日〜終了月の月末日(YYYY-MM-DD)へ変換する。"""
    start = date.fromisoformat(f"{period_from}-01")
    end = date.fromisoformat(f"{period_to}-01")
    return start.isoformat(), month_end(end)
