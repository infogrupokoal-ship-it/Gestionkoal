def test_api_chat_json_csrf_testing_off(app, client):
    # Por defecto TESTING=True (CSRF desactivado). Verificamos que funcione sin header.
    rv_ok = client.post("/api/ai/chat", json={"message": "hola"})
    assert rv_ok.status_code == 200
    # Forzar CSRF activado en runtime
    app.config["TESTING"] = False
    try:
        # Ensure a csrf_token is in the session for the csrf_protect to check against
        with client.session_transaction() as sess:
            sess["csrf_token"] = "a_valid_csrf_token"  # Set a dummy token

        rv = client.post("/api/ai/chat", json={"message": "hola"})
        assert rv.status_code == 400
        data = rv.get_json()
        assert data and data.get("error") == "csrf_failed"
        # Ahora con token correcto
        # Preparar token en sesión visitando login para poblar csrf_token
        client.get("/auth/login")
        with client.session_transaction() as sess:
            token = sess.get("csrf_token")
        assert token
        rv2 = client.post(
            "/api/ai/chat", json={"message": "hola"}, headers={"X-CSRF-Token": token}
        )
        assert rv2.status_code == 200
    finally:
        app.config["TESTING"] = True
