"""Public health-contract tests."""

from fastapi.testclient import TestClient

from mao.main import app


def test_health() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
