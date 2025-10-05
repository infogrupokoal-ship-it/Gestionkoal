import pytest

from backend import create_app  # asumiendo patrón factory; ajusta si no


@pytest.fixture()
def app():
    app = create_app()
    app.config.update(TESTING=True)
    return app

@pytest.fixture()
def client(app):
    return app.test_client()

def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"
