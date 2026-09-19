"""納期状態の判定(詳細設計書4.9.1章)。F-08の表示とF-09の通知で同一関数を使う。"""
from datetime import date
from typing import Literal

from app.core.constants import NOTIFICATION_LEAD_DAYS

DueState = Literal["OVERDUE", "UPCOMING"]


def judge_due_state(due_date: date | None, today: date, lead_days: int = NOTIFICATION_LEAD_DAYS) -> DueState | None:
    """表示対象外はNoneを返す。期限当日は「接近」に含める。"""
    if due_date is None:
        return None
    diff = (due_date - today).days
    if diff < 0:
        return "OVERDUE"
    if diff <= lead_days:
        return "UPCOMING"
    return None
