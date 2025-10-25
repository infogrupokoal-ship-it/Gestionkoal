import pytest
from flask import url_for

from backend import create_app, db
from backend.models import Base
from werkzeug.security import generate_password_hash

def test_kpis_endpoint_authenticated(client, auth):
    auth.login()
    response = client.get("/api/dashboard/kpis")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"]
    data = payload["data"]

    assert data["total"] == 7
    assert data["pendientes"] == 3
    assert data["en_curso"] == 2
    assert data["completados"] == 1
    assert data["cancelados"] == 1
    assert data["abiertos"] == 5 # total - completados - cancelados