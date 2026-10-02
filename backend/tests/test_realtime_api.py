from fastapi.testclient import TestClient

from app.main import app
from conftest import AUTH_HEADERS


def test_authenticated_realtime_ticket_opens_websocket() -> None:
    with TestClient(app) as client:
        ticket_response = client.post(
            "/api/v1/auth/realtime-ticket",
            headers=AUTH_HEADERS["viewer"],
        )
        assert ticket_response.status_code == 200
        ticket = ticket_response.json()["ticket"]

        with client.websocket_connect(f"/api/v1/realtime?ticket={ticket}") as websocket:
            message = websocket.receive_json()

        assert message["type"] == "system.ready"