import io

from app import config


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

    def test_upload_rejects_path_traversal_filename(self, app_client):
        """レビュー指摘2: パストラバーサル(CWE-22)を拒否すること。"""
        created = app_client.post("/api/expenses", json=_valid_expense_payload()).json()
        expense_id = created["id"]
        files = {"file": ("../../evil.jpg", io.BytesIO(b"malicious"), "image/jpeg")}
        response = app_client.post(f"/api/expenses/{expense_id}/attachment", files=files)
        assert response.status_code == 400
        # 意図した保存先ディレクトリの外にファイルが作成されていないことを確認する。
        assert not (config.ATTACHMENTS_DIR.parent / "evil.jpg").exists()

    def test_delete_expense_removes_attachment_files(self, app_client):
        """レビュー指摘10: 経費削除時に添付ファイル実体もあわせて削除されること。"""
        created = app_client.post("/api/expenses", json=_valid_expense_payload()).json()
        expense_id = created["id"]
        files = {"file": ("receipt.png", io.BytesIO(b"fake-image-bytes"), "image/png")}
        app_client.post(f"/api/expenses/{expense_id}/attachment", files=files)
        attachment_dir = config.ATTACHMENTS_DIR / str(expense_id)
        assert attachment_dir.exists()

        delete_response = app_client.delete(f"/api/expenses/{expense_id}")
        assert delete_response.status_code == 204
        assert not attachment_dir.exists()


class TestExpensePeriodValidation:
    """レビュー指摘4: SC-06期間検索(From/To)バリデーション。"""

    def test_list_with_from_after_to_returns_400(self, app_client):
        app_client.post("/api/expenses", json=_valid_expense_payload())
        response = app_client.get(
            "/api/expenses", params={"date_from": "2026-09-30", "date_to": "2026-09-01"}
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "期間(From)は期間(To)より前の日付を入力してください"

    def test_list_with_from_before_to_returns_200(self, app_client):
        app_client.post("/api/expenses", json=_valid_expense_payload(expense_date="2026-09-12"))
        response = app_client.get(
            "/api/expenses", params={"date_from": "2026-09-01", "date_to": "2026-09-30"}
        )
        assert response.status_code == 200
