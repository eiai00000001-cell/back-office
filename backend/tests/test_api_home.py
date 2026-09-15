class TestHomeSummaryApi:
    def test_returns_zero_counts_when_no_invoices(self, app_client):
        response = app_client.get("/api/home/summary")
        assert response.status_code == 200
        assert response.json() == {"unpaid_count": 0, "overdue_count": 0}

    def test_counts_unpaid_invoice(self, app_client):
        client_id = app_client.post("/api/clients", json={"name": "取引先A"}).json()["id"]
        app_client.post(
            "/api/invoices",
            json={
                "client_id": client_id,
                "issue_date": "2026-08-01",
                "due_date": "2026-08-31",
                "items": [
                    {"item_name": "作業", "quantity": "1", "unit_price": 10000, "tax_category": "STANDARD_10"}
                ],
                "remarks": None,
            },
        )
        response = app_client.get("/api/home/summary")
        assert response.json()["unpaid_count"] == 1
