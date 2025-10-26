import pytest
from flask import url_for

from backend import create_app, db

from werkzeug.security import generate_password_hash

def test_login_required_redirects_unauthenticated(client):
    """Test that accessing a login_required route redirects to login page."""
    response = client.get('/clients/', follow_redirects=False)
    assert response.status_code == 302
    assert '/auth/login' in response.headers['Location']

def test_login_required_allows_authenticated(client, auth):
    """Test that accessing a login_required route is successful when authenticated."""
    auth.login()
    response = client.get('/clients/')
    assert response.status_code == 200
    assert b'Lista de Clientes' in response.data # Assuming this text is on the clients list page

