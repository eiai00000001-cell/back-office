class TestClientsApi:
    def test_create_and_list_clients(self, app_client):
        response = app_client.post("/api/clients", json={"name": "株式会社サンプル商事"})
        assert response.status_code == 201
        created = response.json()
        assert created["name"] == "株式会社サンプル商事"

        list_response = app_client.get("/api/clients")
        assert list_response.status_code == 200
        assert len(list_response.json()) == 1

    def test_create_without_name_returns_422(self, app_client):
        response = app_client.post("/api/clients", json={})
        assert response.status_code == 422

    def test_update_unknown_client_returns_404(self, app_client):
        response = app_client.put("/api/clients/9999", json={"name": "X"})
        assert response.status_code == 404

    def test_invalid_postal_code_returns_422(self, app_client):
        response = app_client.post(
            "/api/clients", json={"name": "取引先A", "postal_code": "abcde"}
        )
        assert response.status_code == 422
