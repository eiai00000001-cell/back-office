"""期限API(F-09)。詳細設計書4.10.5・7章。"""
from datetime import date, timedelta


def _payload(**overrides):
    payload = {"name": "契約更新", "due_date": "2026-12-15", "category": "CONTRACT_RENEWAL", "memo": "メモ", "is_recurring": True}
    payload.update(overrides)
    return payload


def _create(app_client, **overrides):
    r = app_client.post("/api/deadlines", json=_payload(**overrides))
    assert r.status_code == 201, r.text
    return r.json()


def test_create_and_get(app_client):
    body = _create(app_client)
    assert body["name"] == "契約更新" and body["is_recurring"] is True and body["category"] == "CONTRACT_RENEWAL"
    got = app_client.get(f"/api/deadlines/{body['id']}").json()
    assert got == body


def test_defaults(app_client):
    r = app_client.post("/api/deadlines", json={"name": "x", "due_date": "2026-12-15"})
    assert r.status_code == 201
    assert r.json()["category"] == "OTHER" and r.json()["is_recurring"] is False and r.json()["memo"] is None


def test_list_sorted_by_due_date(app_client):
    _create(app_client, name="B", due_date="2027-01-01")
    _create(app_client, name="A", due_date="2026-11-01")
    assert [d["name"] for d in app_client.get("/api/deadlines").json()] == ["A", "B"]


def test_due_state_in_response(app_client):
    soon = (date.today() + timedelta(days=3)).isoformat()
    past = (date.today() - timedelta(days=3)).isoformat()
    far = (date.today() + timedelta(days=60)).isoformat()
    states = {d["name"]: d["due_state"] for d in [
        _create(app_client, name="soon", due_date=soon),
        _create(app_client, name="past", due_date=past),
        _create(app_client, name="far", due_date=far),
    ]}
    assert states == {"soon": "UPCOMING", "past": "OVERDUE", "far": None}


def test_update_and_delete(app_client):
    d = _create(app_client)
    r = app_client.put(f"/api/deadlines/{d['id']}", json=_payload(name="更新", is_recurring=False, category="TAX_FILING"))
    assert r.status_code == 200
    assert r.json()["name"] == "更新" and r.json()["is_recurring"] is False and r.json()["category"] == "TAX_FILING"
    assert app_client.delete(f"/api/deadlines/{d['id']}").status_code == 204
    assert app_client.get(f"/api/deadlines/{d['id']}").status_code == 404
    assert app_client.delete(f"/api/deadlines/{d['id']}").status_code == 404
    assert app_client.put(f"/api/deadlines/{d['id']}", json=_payload()).status_code == 404


def test_blank_or_missing_name_returns_message(app_client):
    for body in ({"name": "   ", "due_date": "2026-12-15"}, {"due_date": "2026-12-15"}):
        r = app_client.post("/api/deadlines", json=body)
        assert r.status_code == 422
        assert r.json()["detail"] == "名称を入力してください"


def test_missing_or_blank_due_date_returns_message(app_client):
    for body in ({"name": "x"}, {"name": "x", "due_date": ""}):
        r = app_client.post("/api/deadlines", json=body)
        assert r.status_code == 422
        assert r.json()["detail"] == "期限日を入力してください"


def test_invalid_due_date_format(app_client):
    for bad in ("2026/12/15", "20261215", "2026-13-40", "abc"):
        r = app_client.post("/api/deadlines", json=_payload(due_date=bad))
        assert r.status_code == 422, bad
        assert r.json()["detail"] == "期限日は日付(YYYY-MM-DD)で入力してください"


def test_length_limits(app_client):
    assert app_client.post("/api/deadlines", json=_payload(name="あ" * 101)).status_code == 422
    r = app_client.post("/api/deadlines", json=_payload(memo="あ" * 501))
    assert r.status_code == 422
    assert r.json()["detail"] == "メモは500文字以内で入力してください"
    assert app_client.post("/api/deadlines", json=_payload(name="あ" * 100, memo="あ" * 500)).status_code == 201


def test_invalid_category_rejected(app_client):
    assert app_client.post("/api/deadlines", json=_payload(category="BAD")).status_code == 422


def test_id_range_validation(app_client):
    for bad in ("0", "-1", "9999999999999999999", "abc"):
        r = app_client.get(f"/api/deadlines/{bad}")
        assert r.status_code == 422, bad
        assert r.json()["detail"] == "IDの値が正しくありません"
    assert app_client.get("/api/deadlines/999").status_code == 404
