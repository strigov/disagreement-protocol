from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_ok():
    with TestClient(app, base_url="http://localhost") as client:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}
