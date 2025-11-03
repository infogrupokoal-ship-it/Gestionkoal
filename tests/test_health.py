import pytest


@pytest.fixture()
def client(app):
    return app.test_client()


def test_healthz_ok(client):
    resp = client.get("/healthz/")
    assert resp.status_code == 200
    json_data = resp.get_json()
    assert json_data["status"] == "ok"
    assert json_data["db"] == "ok"


def test_healthz_alias(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["db"] == "ok"
