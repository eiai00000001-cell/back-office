def _create_invoice(app_client):
    client_id = app_client.post("/api/clients", json={"name": "取引先A"}).json()["id"]
    invoice = app_client.post(
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
    ).json()
    return invoice


class TestPaymentsApi:
    def test_record_payment_within_total(self, app_client):
        invoice = _create_invoice(app_client)
        response = app_client.post(
            f"/api/invoices/{invoice['id']}/payments",
            json={"payment_date": "2026-08-15", "amount": 5000, "remarks": None},
        )
        assert response.status_code == 201

        updated_invoice = app_client.get(f"/api/invoices/{invoice['id']}").json()
        assert updated_invoice["payment_status"] == "PARTIALLY_PAID"

    def test_overpayment_without_force_returns_409(self, app_client):
        invoice = _create_invoice(app_client)
        response = app_client.post(
            f"/api/invoices/{invoice['id']}/payments",
            json={"payment_date": "2026-08-15", "amount": 99999, "remarks": None},
        )
        assert response.status_code == 409

    def test_overpayment_with_force_succeeds(self, app_client):
        invoice = _create_invoice(app_client)
        response = app_client.post(
            f"/api/invoices/{invoice['id']}/payments",
            json={"payment_date": "2026-08-15", "amount": 99999, "remarks": None, "force": True},
        )
        assert response.status_code == 201

    def test_list_and_delete_payment(self, app_client):
        invoice = _create_invoice(app_client)
        created = app_client.post(
            f"/api/invoices/{invoice['id']}/payments",
            json={"payment_date": "2026-08-15", "amount": 5000, "remarks": None},
        ).json()

        list_response = app_client.get(f"/api/invoices/{invoice['id']}/payments")
        assert len(list_response.json()) == 1

        delete_response = app_client.delete(f"/api/payments/{created['id']}")
        assert delete_response.status_code == 204
        assert app_client.get(f"/api/invoices/{invoice['id']}/payments").json() == []
