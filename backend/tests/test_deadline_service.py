"""手動登録の期限(F-09)。詳細設計書4.10.5章。DeadlineServiceのテスト。"""
from datetime import date

import pytest

from app.exceptions import NotFoundError
from app.models.notification_acknowledgement import NotificationAcknowledgement
from app.repositories.deadline_repository import DeadlineRepository
from app.repositories.notification_ack_repository import NotificationAckRepository
from app.schemas.deadline import DeadlineCreateRequest, DeadlineUpdateRequest
from app.services.deadline_service import DeadlineService

TODAY = date(2026, 9, 19)


@pytest.fixture()
def service(db_session):
    return DeadlineService(DeadlineRepository(db_session), NotificationAckRepository(db_session))


def _create(service, **overrides):
    payload = {"name": "契約更新", "due_date": "2026-10-01", "category": "CONTRACT_RENEWAL"}
    payload.update(overrides)
    return service.create_deadline(DeadlineCreateRequest(**payload))


def test_create_sets_defaults_and_timestamps(service):
    d = service.create_deadline(DeadlineCreateRequest(name="  期限A ", due_date="2026-10-01"))
    assert d.id is not None
    assert d.name == "期限A"
    assert d.category == "OTHER"
    assert d.is_recurring == 0
    assert d.created_at and d.updated_at


def test_list_orders_by_due_date_then_id(service):
    b = _create(service, name="B", due_date="2026-12-01")
    a = _create(service, name="A", due_date="2026-10-01")
    c = _create(service, name="C", due_date="2026-10-01")
    assert [d.id for d in service.list_deadlines()] == [a.id, c.id, b.id]


def test_update_changes_fields_and_clears_ack_when_due_date_changes(service, db_session):
    d = _create(service)
    db_session.add(
        NotificationAcknowledgement(
            source_type="DEADLINE", source_id=d.id, acknowledged_state="UPCOMING",
            acknowledged_due_date="2026-10-01", acknowledged_at="t",
        )
    )
    db_session.commit()
    updated = service.update_deadline(
        d.id, DeadlineUpdateRequest(name="更新後", due_date="2026-11-01", category="TAX_FILING", memo="m", is_recurring=True)
    )
    assert (updated.name, updated.due_date, updated.category, updated.memo, updated.is_recurring) == (
        "更新後", "2026-11-01", "TAX_FILING", "m", 1,
    )
    assert NotificationAckRepository(db_session).find("DEADLINE", d.id) is None


def test_update_keeps_ack_when_due_date_unchanged(service, db_session):
    d = _create(service)
    db_session.add(
        NotificationAcknowledgement(
            source_type="DEADLINE", source_id=d.id, acknowledged_state="UPCOMING",
            acknowledged_due_date="2026-10-01", acknowledged_at="t",
        )
    )
    db_session.commit()
    service.update_deadline(d.id, DeadlineUpdateRequest(name="名称だけ変更", due_date="2026-10-01"))
    assert NotificationAckRepository(db_session).find("DEADLINE", d.id) is not None


def test_delete_removes_deadline_and_ack(service, db_session):
    d = _create(service)
    db_session.add(
        NotificationAcknowledgement(
            source_type="DEADLINE", source_id=d.id, acknowledged_state="OVERDUE",
            acknowledged_due_date="2026-10-01", acknowledged_at="t",
        )
    )
    db_session.commit()
    service.delete_deadline(d.id)
    assert service.list_deadlines() == []
    assert NotificationAckRepository(db_session).find("DEADLINE", d.id) is None


def test_get_update_delete_unknown_id_raise_not_found(service):
    with pytest.raises(NotFoundError):
        service.get_deadline(999)
    with pytest.raises(NotFoundError):
        service.update_deadline(999, DeadlineUpdateRequest(name="x", due_date="2026-10-01"))
    with pytest.raises(NotFoundError):
        service.delete_deadline(999)


@pytest.mark.parametrize(
    "due,expected",
    [
        ("2026-09-10", "2027-09-10"),  # 超過1年未満 -> 翌年
        ("2024-03-15", "2027-03-15"),  # 長期間放置 -> 今日以降の直近の同月日
        ("2026-09-19", "2027-09-19"),  # 当日は今日以降だが最低1年進める
        ("2028-02-29", "2029-02-28"),  # うるう日(過去日にするため今日を後ろへ)
    ],
)
def test_roll_forward(service, due, expected):
    d = _create(service, due_date=due, is_recurring=True)
    today = date(2028, 3, 5) if due == "2028-02-29" else TODAY
    service.roll_forward(d, today)
    assert d.due_date == expected


def test_roll_forward_updates_updated_at(service):
    d = _create(service, due_date="2026-09-10", is_recurring=True)
    d.updated_at = "2000-01-01T00:00:00"
    service.roll_forward(d, TODAY)
    assert d.updated_at != "2000-01-01T00:00:00"
