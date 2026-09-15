class TestHealthEndpoint:
    def test_returns_ok(self, app_client):
        response = app_client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
