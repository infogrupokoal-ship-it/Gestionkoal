import os
from pathlib import Path
import sqlite3
import pytest
from backend import create_app
from werkzeug.security import generate_password_hash

@pytest.fixture(scope="session")
def app(tmp_path_factory):
    dbfile = tmp_path_factory.mktemp("db", numbered=True) / "test.sqlite"
    if dbfile.exists():
        dbfile.unlink()

    os.environ["FLASK_ENV"] = "testing"
    os.environ["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{dbfile}"

    app = create_app()
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{dbfile}",
        WTF_CSRF_ENABLED=False,
        LOGIN_DISABLED=False,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    schema_sql = Path("schema.sql").read_text(encoding="utf-8")

    with app.app_context():
        db = app.extensions['sqlalchemy']
        raw = db.engine.raw_connection()
        try:
            cur = raw.cursor()
            cur.execute("PRAGMA user_version;")
            (version,) = cur.fetchone()
            if version == 0:
                cur.execute("PRAGMA foreign_keys = ON;")
                raw.executescript(schema_sql)

                pwd = generate_password_hash("password")
                raw.executescript(f"""
                    INSERT OR IGNORE INTO roles(id, code, descripcion)
                      VALUES (1, 'cliente', 'Cliente'), (2, 'admin', 'Administrador');
                    INSERT OR IGNORE INTO users(id, username, email, password_hash, is_active)
                      VALUES (1, 'testuser', 'test@example.com', '{pwd}', 1);
                """)

                cur.execute("PRAGMA user_version = 1;")
                raw.commit()

            assert 'sqlalchemy' in app.extensions, "Flask-SQLAlchemy no registrado en app.extensions"
            assert app.extensions['sqlalchemy'] is db, "db de extensions no coincide con el de la app"
        finally:
            raw.close()

    yield app

    yield app

@pytest.fixture()
def client(app):
    return app.test_client()

@pytest.fixture()
def authed_client(client):
    # simula login (Flask-Login)
    with client.session_transaction() as s:
        s["_user_id"] = "1"   # coincide con el seed de arriba
        s["_fresh"] = True
    return client