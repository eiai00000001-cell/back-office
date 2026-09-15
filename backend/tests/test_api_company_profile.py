class TestCompanyProfileApi:
    def test_get_default_profile(self, app_client):
        response = app_client.get("/api/company-profile")
        assert response.status_code == 200
        assert response.json()["name"] == ""

    def test_update_profile(self, app_client):
        response = app_client.put(
            "/api/company-profile",
            json={"name": "山田 太郎", "business_name": "EIAI TEC", "invoice_registration_number": "T1234567890123"},
        )
        assert response.status_code == 200
        assert response.json()["invoice_registration_number"] == "T1234567890123"

    def test_invalid_registration_number_returns_422(self, app_client):
        response = app_client.put(
            "/api/company-profile", json={"name": "山田 太郎", "invoice_registration_number": "12345"}
        )
        assert response.status_code == 422
