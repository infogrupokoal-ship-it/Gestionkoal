def test_login_rate_limit_and_csrf(client):
    # First GET to set CSRF token in session
    rv_get = client.get('/auth/login')
    assert rv_get.status_code == 200
    # Extract CSRF from session via client context
    with client.session_transaction() as sess:
        token = sess.get('csrf_token')
    assert token

    # Perform 5 bad logins (allowed by rate limit)
    for _ in range(5):
        rv = client.post('/auth/login', data={'username': 'admin', 'password': 'bad', 'csrf_token': token})
        # Either 200 with form re-render or 302 redirect back; ensure not 429 yet
        assert rv.status_code in (200, 400, 302)

    # 6th should be rate limited (429)
    rv6 = client.post('/auth/login', data={'username': 'admin', 'password': 'bad', 'csrf_token': token})
    assert rv6.status_code == 429

    # CSRF missing should be 400
    rv_csrf = client.post('/auth/login', data={'username': 'admin', 'password': 'bad'})
    assert rv_csrf.status_code == 400

