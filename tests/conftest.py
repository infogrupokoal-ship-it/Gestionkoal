from pathlib import Path

import pytest
from sqlalchemy.pool import StaticPool
from backend import create_app, db
from werkzeug.security import generate_password_hash


@pytest.fixture(scope="session")
def app():
    app = create_app()
    app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret",
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        SQLALCHEMY_ENGINE_OPTIONS={
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
        },
    )

    if 'sqlalchemy' not in app.extensions:
        db.init_app(app)

    with app.app_context():
        base_dir = Path(__file__).resolve().parents[1]
        schema_path = base_dir / 'schema.sql'
        script = schema_path.read_text(encoding='utf-8')

        # Crear el esquema completo en la MISMA conexión (importante para :memory:)
        with db.engine.begin() as conn:
            conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
            raw = conn.connection  # sqlite3.Connection
            raw.executescript(script)
            conn.exec_driver_sql("PRAGMA foreign_keys=ON")

        from sqlalchemy import text
        # Semillas mínimas por SQL directo (evita automap)
        with db.engine.begin() as conn:
            # Asegura roles base
            conn.execute(text("INSERT OR IGNORE INTO roles (id, code, descripcion) VALUES (1,'admin','Admin'),(2,'oficina','Oficina'),(4,'autonomo','Autonomo')"))
            # Inserta usuarios
            conn.execute(text("INSERT OR REPLACE INTO users (id, username, password_hash, role, whatsapp_verified) VALUES (:id,:u,:p,:r,:wv)"),
                         [
                           {"id":1,"u":"admin","p":generate_password_hash('password123'),"r":"admin","wv":1},
                           {"id":2,"u":"autonomo","p":generate_password_hash('password123'),"r":"autonomo","wv":1},
                           {"id":3,"u":"oficina","p":generate_password_hash('password123'),"r":"oficina","wv":0},
                         ])
            # Vincula user_roles si la tabla existe
            try:
                admin_role_id = conn.execute(text("SELECT id FROM roles WHERE code='admin'")) .scalar()
                auto_role_id = conn.execute(text("SELECT id FROM roles WHERE code='autonomo'")) .scalar()
                if admin_role_id:
                    conn.execute(text("INSERT OR IGNORE INTO user_roles (user_id, role_id) VALUES (1,:rid)"), {"rid": admin_role_id})
                if auto_role_id:
                    conn.execute(text("INSERT OR IGNORE INTO user_roles (user_id, role_id) VALUES (2,:rid)"), {"rid": auto_role_id})
            except Exception:
                pass

        yield app


@pytest.fixture()
def client(app):
    test_client = app.test_client()
    with test_client.session_transaction() as session:
        session.clear()
    return test_client


@pytest.fixture()
def auth(client):
    class AuthActions:
        def login(self, username="admin", password="password123"):
            response = client.post(
                "/auth/login", data={"username": username, "password": password}
            )
            assert response.status_code == 302
            return response

        def logout(self):
            return client.get("/auth/logout")

    return AuthActions()
