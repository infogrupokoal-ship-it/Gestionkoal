def test_engine_wired(app):
    from backend.extensions import db
    with app.app_context():
        e1 = db.engine
        e2 = db.get_engine()
        assert e1 is e2
        # Ejecuta algo trivial
        with e1.connect() as conn:
            assert conn.exec_driver_sql("select 1").scalar() == 1
