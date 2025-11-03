def test_audit_toggles_requires_admin(client, auth):
    # usuario por defecto admin → debe acceder
    auth.login()
    rv_admin = client.get("/audit/toggles")
    assert rv_admin.status_code == 200

    # Cerrar sesión y probar con usuario no admin
    auth.logout()
    # login como autonomo
    client.post("/auth/login", data={"username": "autonomo", "password": "password123"})
    rv_user = client.get("/audit/toggles")
    assert rv_user.status_code in (302, 403)
    # Si redirige, debería ir al login; si no, 403 por falta de permiso
    if rv_user.status_code == 302:
        assert "/auth/login" in rv_user.headers.get("Location", "")
