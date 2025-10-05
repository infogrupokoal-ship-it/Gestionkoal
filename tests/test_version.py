import pytest

from backend import create_app


@pytest.fixture()
def app():
    app = create_app()
    app.config.update(TESTING=True)
    return app

@pytest.fixture()
def client(app):
    return app.test_client()

def test_version_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    json_data = resp.get_json()
    assert "status" in json_data
    assert json_data["status"] == "ok"
