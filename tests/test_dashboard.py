import pytest

def test_dashboard_kpis(authed_client):
    res = authed_client.get("/api/dashboard/kpis")
    assert res.status_code == 200
    data = res.get_json()
    assert "ok" in data
    assert data["ok"] is True
    assert "data" in data
    assert "total" in data["data"]