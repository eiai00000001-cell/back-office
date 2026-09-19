from datetime import date

from app.utils.due_state import judge_due_state

TODAY = date(2026, 9, 19)


class TestJudgeDueState:
    def test_none_due_date_returns_none(self):
        assert judge_due_state(None, TODAY) is None

    def test_past_due_is_overdue(self):
        assert judge_due_state(date(2026, 9, 18), TODAY) == "OVERDUE"

    def test_today_is_upcoming(self):
        assert judge_due_state(TODAY, TODAY) == "UPCOMING"

    def test_seven_days_ahead_is_upcoming(self):
        assert judge_due_state(date(2026, 9, 26), TODAY) == "UPCOMING"

    def test_eight_days_ahead_is_none(self):
        assert judge_due_state(date(2026, 9, 27), TODAY) is None
