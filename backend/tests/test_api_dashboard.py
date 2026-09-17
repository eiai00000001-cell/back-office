"""財務ダッシュボード(F-07)API。詳細設計書7章・4.8章。区画ごとに4本独立したエンドポイント。"""


class TestDashboardApi:
    def test_sales_and_payments_returns_12_months(self, app_client):
        response = app_client.get("/api/dashboard/sales-and-payments")
        assert response.status_code == 200
        body = response.json()
        assert len(body["sales"]) == 12
        assert len(body["payments"]) == 12

    def test_expenses_returns_monthly_and_category_breakdown(self, app_client):
        response = app_client.get("/api/dashboard/expenses")
        assert response.status_code == 200
        body = response.json()
        assert len(body["monthly"]) == 12
        assert body["by_category"] == []

    def test_profit_loss_returns_12_months(self, app_client):
        response = app_client.get("/api/dashboard/profit-loss")
        assert response.status_code == 200
        body = response.json()
        assert len(body["monthly"]) == 12

    def test_quotes_returns_monthly_and_null_conversion_rate_when_no_data(self, app_client):
        response = app_client.get("/api/dashboard/quotes")
        assert response.status_code == 200
        body = response.json()
        assert len(body["monthly"]) == 12
        assert body["conversion_rate"] is None

    def test_sales_and_payments_reflects_created_invoice(self, app_client):
        client_id = app_client.post("/api/clients", json={"name": "取引先ダッシュボード"}).json()["id"]
        import datetime

        today = datetime.date.today().isoformat()
        app_client.post(
            "/api/invoices",
            json={
                "client_id": client_id,
                "issue_date": today,
                "due_date": today,
                "items": [
                    {"item_name": "作業", "quantity": "1", "unit_price": 10000, "tax_category": "STANDARD_10"}
                ],
                "remarks": None,
            },
        )
        response = app_client.get("/api/dashboard/sales-and-payments")
        body = response.json()
        current_month = today[:7]
        month_item = next(item for item in body["sales"] if item["month"] == current_month)
        assert month_item["amount"] == 11000
