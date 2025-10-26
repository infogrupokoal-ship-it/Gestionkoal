import os


def test_security_headers_present(client, auth, monkeypatch):
    auth.login()
    # Activar CSP para el test
    monkeypatch.setenv('ENABLE_CSP', '1')
    rv = client.get('/')
    assert rv.status_code == 200
    headers = rv.headers
    assert headers.get('X-Content-Type-Options') == 'nosniff'
    assert headers.get('Referrer-Policy') == 'same-origin'
    assert headers.get('X-Frame-Options') == 'DENY'
    assert 'Permissions-Policy' in headers
    # CSP más estricta sin 'unsafe-inline' en scripts
    csp = headers.get('Content-Security-Policy')
    assert csp is not None
    assert "script-src 'self' https://cdn.jsdelivr.net" in csp

