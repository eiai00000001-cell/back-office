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
