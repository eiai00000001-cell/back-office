import io


def _valid_expense_payload(**overrides):
    payload = {
        "expense_date": "2026-09-12",
        "account_category": "消耗品費",
        "amount": 3300,
        "tax_category": "STANDARD_10",
        "payee": "サンプル文具店",
        "payment_method": "CREDIT_CARD",
        "memo": None,
    }
    payload.update(overrides)
    return payload


class TestExpensesApi:
    def test_create_and_list_expenses(self, app_client):
        response = app_client.post("/api/expenses", json=_valid_expense_payload())
        assert response.status_code == 201
        list_response = app_client.get("/api/expenses")
        assert len(list_response.json()) == 1

    def test_create_with_zero_amount_returns_422(self, app_client):
        response = app_client.post("/api/expenses", json=_valid_expense_payload(amount=0))
        assert response.status_code == 422

    def test_summary_endpoint(self, app_client):
        app_client.post("/api/expenses", json=_valid_expense_payload(expense_date="2026-09-01", amount=1000))
        app_client.post("/api/expenses", json=_valid_expense_payload(expense_date="2026-09-12", amount=2000))
        response = app_client.get(
            "/api/expenses/summary", params={"period_from": "2026-09", "period_to": "2026-09"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["by_category"][0]["total_amount"] == 3000
        assert body["by_month"][0]["total_amount"] == 3000

    def test_upload_and_download_attachment(self, app_client):
        created = app_client.post("/api/expenses", json=_valid_expense_payload()).json()
        expense_id = created["id"]

        files = {"file": ("receipt.png", io.BytesIO(b"fake-image-bytes"), "image/png")}
        upload_response = app_client.post(f"/api/expenses/{expense_id}/attachment", files=files)
        assert upload_response.status_code == 200
        assert upload_response.json()["attachment_original_name"] == "receipt.png"

        download_response = app_client.get(f"/api/expenses/{expense_id}/attachment")
        assert download_response.status_code == 200
        assert download_response.content == b"fake-image-bytes"

    def test_upload_rejects_disallowed_extension(self, app_client):
        created = app_client.post("/api/expenses", json=_valid_expense_payload()).json()
        expense_id = created["id"]
        files = {"file": ("receipt.txt", io.BytesIO(b"text"), "text/plain")}
        response = app_client.post(f"/api/expenses/{expense_id}/attachment", files=files)
        assert response.status_code == 400

    def test_download_without_attachment_returns_404(self, app_client):
        created = app_client.post("/api/expenses", json=_valid_expense_payload()).json()
        response = app_client.get(f"/api/expenses/{created['id']}/attachment")
        assert response.status_code == 404
