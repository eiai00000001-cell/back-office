"""通知API(F-09)。詳細設計書4.10.4・4.10.6・7章。"""
from datetime import date, timedelta


def d(offset: int) -> str:
    return (date.today() + timedelta(days=offset)).isoformat()


def _client(app_client):
    return app_client.post("/api/clients", json={"name": "サンプル商事"}).json()["id"]


def _invoice(app_client, cid, due):
    r = app_client.post(
        "/api/invoices",
        json={
            "client_id": cid, "issue_date": "2026-01-01", "due_date": due,
            "items": [{"item_name": "作業", "quantity": 1, "unit_price": 10000, "tax_category": "STANDARD_10"}],
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _project(app_client, name, due):
    return app_client.post("/api/projects", json={"name": name, "due_date": due}).json()


def _deadline(app_client, name, due, recurring=False):
    return app_client.post("/api/deadlines", json={"name": name, "due_date": due, "is_recurring": recurring}).json()


def _ack(app_client, source_type, source_id, method="POST"):
    return app_client.request(method, "/api/notifications/acknowledge", json={"source_type": source_type, "source_id": source_id})


def test_list_returns_all_four_kinds_in_order(app_client):
    cid = _client(app_client)
    inv = _invoice(app_client, cid, d(-2))
    quote = app_client.post(
        "/api/quotes",
        json={"client_id": cid, "issue_date": "2026-01-01", "expiry_date": d(4),
              "items": [{"item_name": "作業", "quantity": 1, "unit_price": 100, "tax_category": "STANDARD_10"}]},
    ).json()
    p = _project(app_client, "サイト", d(1))
    dl = _deadline(app_client, "申告", d(2))
    body = app_client.get("/api/notifications").json()
    assert body["errors"] == []
    assert [(i["source_type"], i["source_id"]) for i in body["items"]] == [
        ("INVOICE_DUE", inv["id"]), ("PROJECT_DUE", p["id"]), ("DEADLINE", dl["id"]), ("QUOTE_EXPIRY", quote["id"]),
    ]
    first = body["items"][0]
    assert first["state"] == "OVERDUE" and first["days_diff"] == -2 and first["link"] == f"/invoices/{inv['id']}"
    assert first["acknowledged"] is False and first["due_date"] == d(-2) and first["category"] is None
    assert body["items"][2]["category"] == "OTHER"


def test_acknowledge_hides_and_include_flag_shows(app_client):
    cid = _client(app_client)
    inv = _invoice(app_client, cid, d(3))
    assert _ack(app_client, "INVOICE_DUE", inv["id"]).status_code == 204
    assert app_client.get("/api/notifications").json()["items"] == []
    shown = app_client.get("/api/notifications", params={"include_acknowledged": "true"}).json()["items"]
    assert len(shown) == 1 and shown[0]["acknowledged"] is True


def test_unacknowledge_restores(app_client):
    cid = _client(app_client)
    inv = _invoice(app_client, cid, d(3))
    _ack(app_client, "INVOICE_DUE", inv["id"])
    assert _ack(app_client, "INVOICE_DUE", inv["id"], method="DELETE").status_code == 204
    assert len(app_client.get("/api/notifications").json()["items"]) == 1
    assert _ack(app_client, "INVOICE_DUE", inv["id"], method="DELETE").status_code == 204  # 冪等


def test_acknowledge_resolved_returns_404_with_message(app_client):
    p = _project(app_client, "遠い案件", d(60))
    r = _ack(app_client, "PROJECT_DUE", p["id"])
    assert r.status_code == 404
    assert r.json()["detail"] == "対象の通知は既に解消されています"


def test_acknowledge_missing_source_returns_404_with_message(app_client):
    for kind in ("INVOICE_DUE", "QUOTE_EXPIRY", "PROJECT_DUE", "DEADLINE"):
        r = _ack(app_client, kind, 12345)
        assert r.status_code == 404, kind
        assert r.json()["detail"] == "通知の元データが見つかりません"


def test_acknowledge_when_collect_fails_is_404_not_500(app_client, monkeypatch):
    from app.repositories.project_repository import ProjectRepository

    p = _project(app_client, "案件", d(2))

    def boom(self, before):
        raise RuntimeError("boom")

    monkeypatch.setattr(ProjectRepository, "list_due_before", boom)
    r = _ack(app_client, "PROJECT_DUE", p["id"])
    assert r.status_code == 404
    assert r.json()["detail"] == "通知の元データが見つかりません"


def test_acknowledge_validation(app_client):
    assert _ack(app_client, "BAD", 1).status_code == 422
    r = _ack(app_client, "INVOICE_DUE", 0)
    assert r.status_code == 422 and r.json()["detail"] == "IDの値が正しくありません"
    assert app_client.post("/api/notifications/acknowledge", json={}).status_code == 422


def test_recurring_overdue_deadline_rolls_forward_on_acknowledge(app_client):
    past = date.today() - timedelta(days=10)
    dl = _deadline(app_client, "申告", past.isoformat(), recurring=True)
    assert _ack(app_client, "DEADLINE", dl["id"]).status_code == 204
    new_due = app_client.get(f"/api/deadlines/{dl['id']}").json()["due_date"]
    assert new_due > date.today().isoformat()
    assert app_client.get("/api/notifications").json()["items"] == []


def test_summary_counts_top5_and_home_independence(app_client):
    cid = _client(app_client)
    for i in range(4):
        _invoice(app_client, cid, d(-i - 1))
    for i in range(3):
        _project(app_client, f"P{i}", d(i))
    body = app_client.get("/api/notifications/summary").json()
    assert body["unacknowledged_count"] == 7
    assert body["overdue_count"] == 4
    assert len(body["items"]) == 5
    assert body["errors"] == []
    # 既存のホームサマリーは通知と独立して従来どおり
    assert app_client.get("/api/home/summary").json() == {"unpaid_count": 4, "overdue_count": 4}


def test_summary_survives_provider_failure(app_client, monkeypatch):
    from app.services import notification_service

    def boom(self, before):
        raise RuntimeError("boom")

    monkeypatch.setattr("app.repositories.quote_repository.QuoteRepository.list_expiring_before", boom)
    cid = _client(app_client)
    _invoice(app_client, cid, d(-1))
    body = app_client.get("/api/notifications/summary")
    assert body.status_code == 200
    assert body.json()["errors"] == ["QUOTE_EXPIRY"]
    assert body.json()["unacknowledged_count"] == 1
    assert notification_service  # noqa: keep import used


def test_deleting_source_removes_ack_record(app_client):
    cid = _client(app_client)
    inv = _invoice(app_client, cid, d(3))
    _ack(app_client, "INVOICE_DUE", inv["id"])
    assert app_client.delete(f"/api/invoices/{inv['id']}").status_code == 204
    assert app_client.get("/api/notifications", params={"include_acknowledged": "true"}).json()["items"] == []


def test_done_project_and_converted_quote_and_paid_invoice_do_not_notify(app_client):
    cid = _client(app_client)
    inv = _invoice(app_client, cid, d(-1))
    app_client.post(f"/api/invoices/{inv['id']}/payments", json={"payment_date": d(0), "amount": 11000})
    p = _project(app_client, "完了案件", d(-1))
    app_client.patch(f"/api/projects/{p['id']}/status", json={"status": "DONE"})
    quote = app_client.post(
        "/api/quotes",
        json={"client_id": cid, "issue_date": "2026-01-01", "expiry_date": d(1),
              "items": [{"item_name": "作業", "quantity": 1, "unit_price": 100, "tax_category": "STANDARD_10"}]},
    ).json()
    assert app_client.post(f"/api/quotes/{quote['id']}/convert-to-invoice").status_code == 201
    items = app_client.get("/api/notifications").json()["items"]
    # 変換後の請求書は発行日・支払期限が未設定のため通知に出ない
    assert items == []


def test_missing_source_type_uses_japanese_label(app_client):
    r = app_client.post("/api/notifications/acknowledge", json={"source_id": 1})
    assert r.status_code == 422
    assert r.json()["detail"] == "通知の種類は必須です"


def _orphan_ack(source_type, source_id):
    import app.database as database
    from app.models.notification_acknowledgement import NotificationAcknowledgement as Ack

    with database.SessionLocal() as s:
        s.add(Ack(source_type=source_type, source_id=source_id, acknowledged_state="UPCOMING",
                  acknowledged_due_date=d(3), acknowledged_at="2026-01-01T00:00:00"))
        s.commit()


def _ack_count(source_type, source_id):
    import app.database as database
    from app.models.notification_acknowledgement import NotificationAcknowledgement as Ack

    with database.SessionLocal() as s:
        return s.query(Ack).filter(Ack.source_type == source_type, Ack.source_id == source_id).count()


def test_acknowledge_deleted_source_removes_orphan_ack_even_though_404(app_client):
    """指摘37: 通知元が削除済みなら404を返しつつ、残っていた確認済み記録の削除は永続化される(4.10.4)。"""
    _orphan_ack("INVOICE_DUE", 999)
    assert _ack_count("INVOICE_DUE", 999) == 1
    r = _ack(app_client, "INVOICE_DUE", 999)
    assert r.status_code == 404
    assert r.json()["detail"] == "通知の元データが見つかりません"
    assert _ack_count("INVOICE_DUE", 999) == 0


def test_acknowledge_when_source_exists_check_fails_is_404_and_logged(app_client, monkeypatch, caplog):
    """指摘38: source_existsの例外もcollectと同様に404へ変換し、ログには種類とトレースのみ残す。"""
    from app.services.notification_service import ProjectDueProvider

    def boom(self, source_id):
        raise RuntimeError("boom")

    monkeypatch.setattr(ProjectDueProvider, "source_exists", boom)
    with caplog.at_level("ERROR", logger="app"):
        r = _ack(app_client, "PROJECT_DUE", 4242)
    assert r.status_code == 404
    assert r.json()["detail"] == "通知の元データが見つかりません"
    assert any("PROJECT_DUE" in rec.getMessage() and rec.exc_info for rec in caplog.records)
