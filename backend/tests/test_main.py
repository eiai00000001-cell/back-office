import logging

from fastapi.testclient import TestClient

from app.main import app as fastapi_app
from app.repositories.client_repository import ClientRepository


class TestRequestValidationErrorHandling:
    """レビュー指摘1: 422応答のdetailは配列ではなく単一の日本語文字列であること。"""

    def test_missing_name_returns_single_string_detail(self, app_client):
        response = app_client.post("/api/clients", json={"name": ""})
        assert response.status_code == 422
        detail = response.json()["detail"]
        assert isinstance(detail, str)
        assert detail == "名称を入力してください"

    def test_invoice_item_zero_quantity_returns_japanese_message(self, app_client):
        client_response = app_client.post("/api/clients", json={"name": "取引先A"})
        client_id = client_response.json()["id"]
        response = app_client.post(
            "/api/invoices",
            json={
                "client_id": client_id,
                "issue_date": "2026-08-01",
                "due_date": "2026-08-31",
                "items": [
                    {
                        "item_name": "作業",
                        "quantity": 0,
                        "unit_price": 1000,
                        "tax_category": "STANDARD_10",
                    }
                ],
                "remarks": None,
            },
        )
        assert response.status_code == 422
        detail = response.json()["detail"]
        assert isinstance(detail, str)
        assert detail == "数量は0より大きい数値で入力してください"

    def test_invoice_item_zero_unit_price_returns_japanese_message(self, app_client):
        client_response = app_client.post("/api/clients", json={"name": "取引先A"})
        client_id = client_response.json()["id"]
        response = app_client.post(
            "/api/invoices",
            json={
                "client_id": client_id,
                "issue_date": "2026-08-01",
                "due_date": "2026-08-31",
                "items": [
                    {
                        "item_name": "作業",
                        "quantity": 1,
                        "unit_price": 0,
                        "tax_category": "STANDARD_10",
                    }
                ],
                "remarks": None,
            },
        )
        assert response.status_code == 422
        assert response.json()["detail"] == "単価は0より大きい数値で入力してください"

    def test_expense_zero_amount_returns_japanese_message(self, app_client):
        response = app_client.post(
            "/api/expenses",
            json={
                "expense_date": "2026-09-12",
                "account_category": "消耗品費",
                "amount": 0,
                "tax_category": "STANDARD_10",
                "payee": None,
                "payment_method": None,
                "memo": None,
            },
        )
        assert response.status_code == 422
        assert response.json()["detail"] == "金額は0より大きい数値で入力してください"


class TestUnexpectedErrorLogging:
    """レビュー指摘3: 予期しない例外はUvicornの標準エラーログへ記録されること。"""

    def test_unexpected_exception_is_logged_and_returns_500(self, app_client, monkeypatch, caplog):
        def _boom(self):
            raise RuntimeError("boom")

        monkeypatch.setattr(ClientRepository, "list_all", _boom)

        # app_clientが既に依存関係のオーバーライドを設定済みのため、同じappインスタンスに対し
        # raise_server_exceptions=Falseのクライアントで呼び出し、例外処理ハンドラの応答を検証する。
        with caplog.at_level(logging.ERROR, logger="app"):
            with TestClient(fastapi_app, raise_server_exceptions=False) as client:
                response = client.get("/api/clients")

        assert response.status_code == 500
        assert response.json() == {"detail": "処理に失敗しました。しばらくしてから再度お試しください"}
        assert any("Unhandled exception" in record.message for record in caplog.records)
        assert any(record.exc_info is not None for record in caplog.records)
