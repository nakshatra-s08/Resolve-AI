from fastapi import status
from fastapi.testclient import TestClient


def test_health_check_returns_200_and_status_ok(client: TestClient):
    """GET /api/health returns HTTP 200 and {'status': 'ok'}."""
    response = client.get("/api/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data == {"status": "ok"}
