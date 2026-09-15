def _create_client(app_client) -> int:
    response = app_client.post("/api/clients", json={"name": "株式会社サンプル商事"})
    return response.json()["id"]


def _valid_invoice_payload(client_id, **overrides):
    payload = {
        "client_id": client_id,
        "issue_date": "2026-08-01",
        "due_date": "2026-08-31",
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


class TestInvoicesApi:
    def test_create_invoice_returns_201_with_calculated_totals(self, app_client):
        client_id = _create_client(app_client)
        response = app_client.post("/api/invoices", json=_valid_invoice_payload(client_id))
        assert response.status_code == 201
        body = response.json()
        assert body["total_amount"] == 330000
        assert body["payment_status"] == "UNPAID"
        assert body["invoice_number"].endswith("-0001")

    def test_create_invoice_with_empty_items_returns_400(self, app_client):
        client_id = _create_client(app_client)
        response = app_client.post("/api/invoices", json=_valid_invoice_payload(client_id, items=[]))
        assert response.status_code == 400

    def test_create_invoice_without_issue_date_returns_400(self, app_client):
        client_id = _create_client(app_client)
        response = app_client.post("/api/invoices", json=_valid_invoice_payload(client_id, issue_date=None))
        assert response.status_code == 400

    def test_get_and_list_and_delete_invoice(self, app_client):
        client_id = _create_client(app_client)
        created = app_client.post("/api/invoices", json=_valid_invoice_payload(client_id)).json()

        get_response = app_client.get(f"/api/invoices/{created['id']}")
        assert get_response.status_code == 200

        list_response = app_client.get("/api/invoices")
        assert len(list_response.json()) == 1

        delete_response = app_client.delete(f"/api/invoices/{created['id']}")
        assert delete_response.status_code == 204
        assert app_client.get(f"/api/invoices/{created['id']}").status_code == 404

    def test_get_invoice_pdf_returns_pdf_content_type(self, app_client):
        client_id = _create_client(app_client)
        created = app_client.post("/api/invoices", json=_valid_invoice_payload(client_id)).json()
        response = app_client.get(f"/api/invoices/{created['id']}/pdf")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.content.startswith(b"%PDF")

    def test_filter_invoices_by_payment_status(self, app_client):
        client_id = _create_client(app_client)
        created = app_client.post("/api/invoices", json=_valid_invoice_payload(client_id)).json()

        unpaid = app_client.get("/api/invoices", params={"payment_status": "UNPAID"})
        assert len(unpaid.json()) == 1

        paid = app_client.get("/api/invoices", params={"payment_status": "PAID"})
        assert len(paid.json()) == 0
