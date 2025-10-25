import pytest

# No need to import create_app here, as the app fixture is provided by conftest.py

@pytest.fixture()
def client(app): # Use the app fixture from conftest.py
    return app.test_client()

def test_version_ok(client):
    resp = client.get("/healthz") # Call /healthz instead of /health
    assert resp.status_code == 200
    json_data = resp.get_json()
    assert json_data["status"] == "ok"
    assert json_data["db"] in ["ok", "skipped"] # Check for the 'db' key