def _create_client(app_client) -> int:
    response = app_client.post("/api/clients", json={"name": "株式会社サンプル商事"})
    return response.json()["id"]


def _valid_quote_payload(client_id, **overrides):
    payload = {
        "client_id": client_id,
        "issue_date": "2026-07-25",
        "expiry_date": "2026-08-25",
        "status": "DRAFT",
        "items": [
            {
                "item_name": "Webサイト制作作業",
                "quantity": "1",
                "unit_price": 300000,
                "tax_category": "STANDARD_10",
            }
        ],
        "remarks": None,
    }
    payload.update(overrides)
    return payload


class TestQuotesApi:
    def test_create_quote_returns_201(self, app_client):
        client_id = _create_client(app_client)
        response = app_client.post("/api/quotes", json=_valid_quote_payload(client_id))
        assert response.status_code == 201
        assert response.json()["total_amount"] == 330000

    def test_get_quote_pdf(self, app_client):
        client_id = _create_client(app_client)
        created = app_client.post("/api/quotes", json=_valid_quote_payload(client_id)).json()
        response = app_client.get(f"/api/quotes/{created['id']}/pdf")
        assert response.status_code == 200
        assert response.content.startswith(b"%PDF")

    def test_filter_quotes_by_status(self, app_client):
        client_id = _create_client(app_client)
        app_client.post("/api/quotes", json=_valid_quote_payload(client_id, status="DRAFT"))
        app_client.post("/api/quotes", json=_valid_quote_payload(client_id, status="CONFIRMED"))
        confirmed = app_client.get("/api/quotes", params={"status": "CONFIRMED"})
        assert len(confirmed.json()) == 1


class TestConvertToInvoiceApi:
    def test_converts_quote_to_invoice(self, app_client):
        client_id = _create_client(app_client)
        quote = app_client.post("/api/quotes", json=_valid_quote_payload(client_id)).json()
        response = app_client.post(f"/api/quotes/{quote['id']}/convert-to-invoice")
        assert response.status_code == 201
        invoice = response.json()
        assert invoice["source_quote_id"] == quote["id"]
        assert invoice["issue_date"] is None
        assert invoice["due_date"] is None

    def test_returns_409_when_already_converted(self, app_client):
        client_id = _create_client(app_client)
        quote = app_client.post("/api/quotes", json=_valid_quote_payload(client_id)).json()
        app_client.post(f"/api/quotes/{quote['id']}/convert-to-invoice")
        second_attempt = app_client.post(f"/api/quotes/{quote['id']}/convert-to-invoice")
        assert second_attempt.status_code == 409
        assert "変換済み" in second_attempt.json()["detail"]

    def test_returns_404_for_unknown_quote(self, app_client):
        response = app_client.post("/api/quotes/9999/convert-to-invoice")
        assert response.status_code == 404
