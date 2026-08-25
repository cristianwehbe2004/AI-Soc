from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.health import HealthResponse


def test_health_endpoint_returns_connected_services(monkeypatch) -> None:
    async def fake_check(self) -> HealthResponse:
        return HealthResponse(status="healthy", database="connected", redis="connected")

    monkeypatch.setattr("app.services.health.HealthService.check", fake_check)

    client = TestClient(app)
    response = client.get("/api/v1/health")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "status": "healthy",
        "database": "connected",
        "redis": "connected",
    }


def test_health_endpoint_returns_503_when_dependency_fails(monkeypatch) -> None:
    async def fake_check(self) -> HealthResponse:
        return HealthResponse(status="degraded", database="disconnected", redis="connected")

    monkeypatch.setattr("app.services.health.HealthService.check", fake_check)

    client = TestClient(app)
    response = client.get("/api/v1/health")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["detail"] == {
        "status": "degraded",
        "database": "disconnected",
        "redis": "connected",
    }
