from datetime import date, timedelta


def _client(app_client, name="サンプル商事"):
    return app_client.post("/api/clients", json={"name": name}).json()["id"]


def _project(app_client, **overrides):
    payload = {"name": "サイト制作"}
    payload.update(overrides)
    response = app_client.post("/api/projects", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _invoice_payload(client_id, **overrides):
    payload = {
        "client_id": client_id,
        "issue_date": "2026-09-01",
        "due_date": "2026-09-30",
        "items": [{"item_name": "作業", "quantity": 1, "unit_price": 10000, "tax_category": "STANDARD_10"}],
    }
    payload.update(overrides)
    return payload


def _quote_payload(client_id, **overrides):
    payload = {
        "client_id": client_id,
        "issue_date": "2026-09-01",
        "expiry_date": "2026-09-30",
        "items": [{"item_name": "作業", "quantity": 1, "unit_price": 10000, "tax_category": "STANDARD_10"}],
    }
    payload.update(overrides)
    return payload


def _expense_payload(**overrides):
    payload = {"expense_date": "2026-09-05", "account_category": "消耗品費", "amount": 1000}
    payload.update(overrides)
    return payload


class TestProjectCrud:
    def test_create_defaults_and_trims_name(self, app_client):
        body = _project(app_client, name="  案件A  ")
        assert body["name"] == "案件A"
        assert body["status"] == "NOT_STARTED"
        assert body["due_date"] is None
        assert body["client_id"] is None

    def test_blank_name_returns_422_with_message(self, app_client):
        response = app_client.post("/api/projects", json={"name": "   "})
        assert response.status_code == 422
        assert response.json()["detail"] == "案件名を入力してください"

    def test_name_over_100_chars_returns_422(self, app_client):
        assert app_client.post("/api/projects", json={"name": "あ" * 101}).status_code == 422

    def test_description_over_1000_chars_returns_422(self, app_client):
        assert app_client.post("/api/projects", json={"name": "a", "description": "x" * 1001}).status_code == 422

    def test_invalid_status_and_date_return_422(self, app_client):
        assert app_client.post("/api/projects", json={"name": "a", "status": "BAD"}).status_code == 422
        assert app_client.post("/api/projects", json={"name": "a", "due_date": "2026/09/01"}).status_code == 422

    def test_due_date_only_accepts_yyyy_mm_dd(self, app_client):
        for bad in ("20260919", "2026-W38-1", "2026-9-1", "2026-02-30", "2026-09-19T10:00"):
            response = app_client.post("/api/projects", json={"name": "a", "due_date": bad})
            assert response.status_code == 422, bad
            assert "YYYY-MM-DD" in response.json()["detail"]

    def test_due_date_is_stored_as_normalized_iso_date(self, app_client):
        body = app_client.post("/api/projects", json={"name": "a", "due_date": " 2026-09-19 "})
        assert body.status_code in (200, 201)
        assert body.json()["due_date"] == "2026-09-19"

    def test_unknown_client_returns_422(self, app_client):
        assert app_client.post("/api/projects", json={"name": "a", "client_id": 999}).status_code == 422

    def test_update_and_get(self, app_client):
        cid = _client(app_client)
        pid = _project(app_client)["id"]
        response = app_client.put(
            f"/api/projects/{pid}",
            json={"name": "更新後", "client_id": cid, "status": "IN_PROGRESS", "due_date": "2026-12-31", "description": "メモ"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "IN_PROGRESS"
        detail = app_client.get(f"/api/projects/{pid}").json()
        assert detail["name"] == "更新後"
        assert detail["client_name"] == "サンプル商事"

    def test_get_unknown_returns_404(self, app_client):
        assert app_client.get("/api/projects/999").status_code == 404
        assert app_client.put("/api/projects/999", json={"name": "a"}).status_code == 404
        assert app_client.delete("/api/projects/999").status_code == 404
        assert app_client.patch("/api/projects/999/status", json={"status": "DONE"}).status_code == 404


class TestProjectList:
    def test_order_by_due_date_nulls_last_then_id(self, app_client):
        a = _project(app_client, name="A", due_date="2026-12-01")["id"]
        b = _project(app_client, name="B")["id"]
        c = _project(app_client, name="C", due_date="2026-10-01")["id"]
        d = _project(app_client, name="D")["id"]
        ids = [p["id"] for p in app_client.get("/api/projects").json()]
        assert ids == [c, a, b, d]

    def test_filters_and_counts(self, app_client):
        cid = _client(app_client)
        p1 = _project(app_client, client_id=cid, status="DONE")["id"]
        _project(app_client, name="other")
        app_client.post("/api/quotes", json=_quote_payload(cid, project_id=p1))
        app_client.post("/api/invoices", json=_invoice_payload(cid, project_id=p1))
        app_client.post("/api/invoices", json=_invoice_payload(cid, project_id=p1))
        rows = app_client.get("/api/projects", params={"status": "DONE", "client_id": cid}).json()
        assert len(rows) == 1
        assert rows[0]["client_name"] == "サンプル商事"
        assert rows[0]["quote_count"] == 1
        assert rows[0]["invoice_count"] == 2
        assert len(app_client.get("/api/projects").json()) == 2

    def test_due_state(self, app_client):
        today = date.today()
        _project(app_client, name="over", due_date=(today - timedelta(days=1)).isoformat())
        _project(app_client, name="soon", due_date=today.isoformat())
        _project(app_client, name="far", due_date=(today + timedelta(days=30)).isoformat())
        _project(app_client, name="done", status="DONE", due_date=(today - timedelta(days=5)).isoformat())
        _project(app_client, name="none")
        states = {p["name"]: p["due_state"] for p in app_client.get("/api/projects").json()}
        assert states == {"over": "OVERDUE", "soon": "UPCOMING", "far": None, "done": None, "none": None}


class TestStatusChange:
    def test_patch_status_only_changes_status(self, app_client):
        pid = _project(app_client, name="X", description="d")["id"]
        response = app_client.patch(f"/api/projects/{pid}/status", json={"status": "WAITING_REVIEW"})
        assert response.status_code == 200
        assert response.json()["status"] == "WAITING_REVIEW"
        assert response.json()["name"] == "X"
        assert response.json()["description"] == "d"

    def test_patch_invalid_status_returns_422(self, app_client):
        pid = _project(app_client)["id"]
        assert app_client.patch(f"/api/projects/{pid}/status", json={"status": "X"}).status_code == 422


class TestProjectDetailSummary:
    def test_summary_includes_documents_without_issue_date(self, app_client):
        cid = _client(app_client)
        pid = _project(app_client, client_id=cid)["id"]
        q = app_client.post("/api/quotes", json=_quote_payload(cid, project_id=pid)).json()
        inv = app_client.post("/api/invoices", json=_invoice_payload(cid, project_id=pid)).json()
        converted = app_client.post(f"/api/quotes/{q['id']}/convert-to-invoice").json()
        assert converted["project_id"] == pid
        app_client.post(f"/api/invoices/{inv['id']}/payments", json={"payment_date": "2026-09-10", "amount": 4000})
        detail = app_client.get(f"/api/projects/{pid}").json()
        s = detail["summary"]
        assert s["quote_count"] == 1 and s["quote_total"] == q["total_amount"]
        assert s["invoice_count"] == 2
        assert s["invoice_total"] == inv["total_amount"] + converted["total_amount"]
        assert s["paid_total"] == 4000
        assert s["unpaid_total"] == inv["total_amount"] - 4000 + converted["total_amount"]
        by_id = {i["id"]: i for i in detail["invoices"]}
        assert by_id[inv["id"]]["payment_status"] == "PARTIALLY_PAID"
        assert by_id[converted["id"]]["issue_date"] is None
        assert detail["quotes"][0]["quote_number"] == q["quote_number"]

    def test_unpaid_total_floors_overpayment_at_zero(self, app_client):
        cid = _client(app_client)
        pid = _project(app_client)["id"]
        inv = app_client.post("/api/invoices", json=_invoice_payload(cid, project_id=pid)).json()
        app_client.post(
            f"/api/invoices/{inv['id']}/payments",
            json={"payment_date": "2026-09-10", "amount": inv["total_amount"] + 500, "force": True},
        )
        assert app_client.get(f"/api/projects/{pid}").json()["summary"]["unpaid_total"] == 0

    def test_empty_project_summary_is_zero(self, app_client):
        pid = _project(app_client)["id"]
        s = app_client.get(f"/api/projects/{pid}").json()["summary"]
        assert s == {
            "quote_count": 0, "quote_total": 0, "invoice_count": 0,
            "invoice_total": 0, "paid_total": 0, "unpaid_total": 0,
        }


class TestProjectDelete:
    def test_delete_keeps_documents_and_children(self, app_client):
        cid = _client(app_client)
        pid = _project(app_client)["id"]
        q = app_client.post("/api/quotes", json=_quote_payload(cid, project_id=pid)).json()
        inv = app_client.post("/api/invoices", json=_invoice_payload(cid, project_id=pid)).json()
        ex = app_client.post("/api/expenses", json=_expense_payload(project_id=pid)).json()
        app_client.post(f"/api/invoices/{inv['id']}/payments", json={"payment_date": "2026-09-10", "amount": 100})
        assert app_client.delete(f"/api/projects/{pid}").status_code == 204
        assert app_client.get(f"/api/projects/{pid}").status_code == 404
        got_inv = app_client.get(f"/api/invoices/{inv['id']}").json()
        assert got_inv["project_id"] is None and got_inv["project_name"] is None
        assert len(got_inv["items"]) == 1 and len(got_inv["payments"]) == 1
        assert app_client.get(f"/api/quotes/{q['id']}").json()["project_id"] is None
        assert app_client.get(f"/api/expenses/{ex['id']}").json()["project_id"] is None


class TestLinkApi:
    def test_link_move_and_unlink_invoice(self, app_client):
        cid = _client(app_client)
        p1 = _project(app_client, name="P1")["id"]
        p2 = _project(app_client, name="P2")["id"]
        inv = app_client.post("/api/invoices", json=_invoice_payload(cid)).json()
        r = app_client.put(f"/api/invoices/{inv['id']}/project", json={"project_id": p1})
        assert r.status_code == 200 and r.json()["project_name"] == "P1"
        r = app_client.put(f"/api/invoices/{inv['id']}/project", json={"project_id": p2})
        assert r.json()["project_id"] == p2
        r = app_client.put(f"/api/invoices/{inv['id']}/project", json={"project_id": None})
        assert r.json()["project_id"] is None

    def test_link_quote_and_expense(self, app_client):
        cid = _client(app_client)
        pid = _project(app_client, name="P1")["id"]
        q = app_client.post("/api/quotes", json=_quote_payload(cid)).json()
        e = app_client.post("/api/expenses", json=_expense_payload()).json()
        assert app_client.put(f"/api/quotes/{q['id']}/project", json={"project_id": pid}).json()["project_name"] == "P1"
        assert app_client.put(f"/api/expenses/{e['id']}/project", json={"project_id": pid}).json()["project_id"] == pid

    def test_link_unknown_project_is_422_and_unknown_document_is_404(self, app_client):
        cid = _client(app_client)
        inv = app_client.post("/api/invoices", json=_invoice_payload(cid)).json()
        r = app_client.put(f"/api/invoices/{inv['id']}/project", json={"project_id": 999})
        assert r.status_code == 422
        assert "案件が見つかりません" in r.json()["detail"]
        assert app_client.put("/api/invoices/999/project", json={"project_id": None}).status_code == 404
        assert app_client.put("/api/quotes/999/project", json={"project_id": None}).status_code == 404
        assert app_client.put("/api/expenses/999/project", json={"project_id": None}).status_code == 404

    def test_link_works_on_converted_invoice_without_dates(self, app_client):
        cid = _client(app_client)
        pid = _project(app_client)["id"]
        q = app_client.post("/api/quotes", json=_quote_payload(cid)).json()
        inv = app_client.post(f"/api/quotes/{q['id']}/convert-to-invoice").json()
        assert inv["issue_date"] is None
        r = app_client.put(f"/api/invoices/{inv['id']}/project", json={"project_id": pid})
        assert r.status_code == 200 and r.json()["issue_date"] is None

    def test_link_does_not_touch_other_fields(self, app_client):
        cid = _client(app_client)
        pid = _project(app_client)["id"]
        inv = app_client.post("/api/invoices", json=_invoice_payload(cid, remarks="備考")).json()
        r = app_client.put(f"/api/invoices/{inv['id']}/project", json={"project_id": pid}).json()
        assert r["remarks"] == "備考" and r["total_amount"] == inv["total_amount"] and len(r["items"]) == 1


class TestNormalSaveProjectId:
    """詳細設計書4.9.5・4.13.2: 通常のPOST/PUTはproject_idをリクエスト値(省略=null)で更新する。"""

    def test_create_without_project_id_works(self, app_client):
        cid = _client(app_client)
        assert app_client.post("/api/invoices", json=_invoice_payload(cid)).json()["project_id"] is None
        assert app_client.post("/api/quotes", json=_quote_payload(cid)).json()["project_id"] is None
        assert app_client.post("/api/expenses", json=_expense_payload()).json()["project_id"] is None

    def test_put_with_project_id_keeps_and_omission_clears(self, app_client):
        cid = _client(app_client)
        pid = _project(app_client, name="P")["id"]
        inv = app_client.post("/api/invoices", json=_invoice_payload(cid, project_id=pid)).json()
        assert inv["project_name"] == "P"
        kept = app_client.put(f"/api/invoices/{inv['id']}", json=_invoice_payload(cid, project_id=pid)).json()
        assert kept["project_id"] == pid
        cleared = app_client.put(f"/api/invoices/{inv['id']}", json=_invoice_payload(cid)).json()
        assert cleared["project_id"] is None

    def test_put_quote_and_expense_project_id(self, app_client):
        cid = _client(app_client)
        pid = _project(app_client)["id"]
        q = app_client.post("/api/quotes", json=_quote_payload(cid, project_id=pid)).json()
        assert app_client.put(f"/api/quotes/{q['id']}", json=_quote_payload(cid, project_id=pid)).json()["project_id"] == pid
        assert app_client.put(f"/api/quotes/{q['id']}", json=_quote_payload(cid)).json()["project_id"] is None
        e = app_client.post("/api/expenses", json=_expense_payload(project_id=pid)).json()
        assert app_client.put(f"/api/expenses/{e['id']}", json=_expense_payload(project_id=pid)).json()["project_id"] == pid

    def test_unknown_project_id_returns_422(self, app_client):
        cid = _client(app_client)
        assert app_client.post("/api/invoices", json=_invoice_payload(cid, project_id=999)).status_code == 422
        assert app_client.post("/api/quotes", json=_quote_payload(cid, project_id=999)).status_code == 422
        assert app_client.post("/api/expenses", json=_expense_payload(project_id=999)).status_code == 422

    def test_list_endpoints_include_project_name_and_keep_row_count(self, app_client):
        cid = _client(app_client)
        pid = _project(app_client, name="P")["id"]
        app_client.post("/api/invoices", json=_invoice_payload(cid, project_id=pid))
        app_client.post("/api/invoices", json=_invoice_payload(cid))
        app_client.post("/api/quotes", json=_quote_payload(cid, project_id=pid))
        app_client.post("/api/quotes", json=_quote_payload(cid))
        invoices = app_client.get("/api/invoices").json()
        quotes = app_client.get("/api/quotes").json()
        assert len(invoices) == 2 and len(quotes) == 2
        assert sorted(i["project_name"] or "" for i in invoices) == ["", "P"]
        assert sorted(q["project_name"] or "" for q in quotes) == ["", "P"]


class TestConversionProjectCarryOver:
    def test_project_carried_and_independent(self, app_client):
        cid = _client(app_client)
        p1 = _project(app_client, name="P1")["id"]
        p2 = _project(app_client, name="P2")["id"]
        q = app_client.post("/api/quotes", json=_quote_payload(cid, project_id=p1)).json()
        inv = app_client.post(f"/api/quotes/{q['id']}/convert-to-invoice").json()
        assert inv["project_id"] == p1
        app_client.put(f"/api/invoices/{inv['id']}/project", json={"project_id": p2})
        assert app_client.get(f"/api/quotes/{q['id']}").json()["project_id"] == p1
        assert app_client.post(f"/api/quotes/{q['id']}/convert-to-invoice").status_code == 409

    def test_no_project_stays_null(self, app_client):
        cid = _client(app_client)
        q = app_client.post("/api/quotes", json=_quote_payload(cid)).json()
        assert app_client.post(f"/api/quotes/{q['id']}/convert-to-invoice").json()["project_id"] is None
