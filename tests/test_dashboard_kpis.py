import pytest

def test_kpis_endpoint_authenticated(authed_client):
    """Tests that the KPI endpoint is accessible with an authenticated client."""
    response = authed_client.get("/api/dashboard/kpis")
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["ok"] is True
    assert "data" in json_data