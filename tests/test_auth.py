import pytest

def test_login_success_redirect(client):
    """Tests that a successful login POST results in a redirect."""
    with client:
        rv = client.post(
            "/auth/login",
            data={"username": "testuser", "password": "password"},
            follow_redirects=False,
        )
        assert rv.status_code == 302
        assert rv.headers.get("Location") == "/"

def test_protected_routes_and_logout(authed_client):
    """Tests that a protected route is accessible and that logout works."""
    # 1) Check that a protected route is accessible with a pre-authenticated client
    rv = authed_client.get("/api/dashboard/kpis")
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["ok"] is True

    # 2) Logout
    rv = authed_client.get("/auth/logout", follow_redirects=False)
    assert rv.status_code == 302

    # 3) Check that the protected route is no longer accessible
    rv = authed_client.get("/api/dashboard/kpis", follow_redirects=False)
    assert rv.status_code == 302
    assert "/auth/login" in rv.headers.get("Location", "")

def test_login_wrong_password(client):
    """Tests login with an incorrect password."""
    with client:
        rv = client.post(
            "/auth/login",
            data={"username": "testuser", "password": "wrongpassword"},
            follow_redirects=True,
        )
        assert rv.status_code == 200
        assert b"Contrase" in rv.data or b"credencial" in rv.data

def test_unauthenticated_access(client):
    """Tests that a protected route redirects when not logged in."""
    rv = client.get('/api/dashboard/kpis', follow_redirects=False)
    assert rv.status_code == 302
    assert '/auth/login' in rv.location
