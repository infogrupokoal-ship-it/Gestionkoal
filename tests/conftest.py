# tests/conftest.py
import pytest
from sqlalchemy import inspect
from backend import create_app, db
from backend.models import Base, get_table_class, session_scope
from backend.db_utils import _execute_sql
from werkzeug.security import generate_password_hash

@pytest.fixture(scope="session")
def app():
    app = create_app()
    app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret",
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        SQLALCHEMY_ENGINE_OPTIONS={"connect_args": {"check_same_thread": False}},
    )

    if 'sqlalchemy' not in app.extensions:
        db.init_app(app)

    with app.app_context():
        # 1) Crear tablas desde schema.sql usando la MISMA conexión/engine y COMMIT automático
        with app.open_resource('schema.sql') as f:
            script = f.read().decode('utf-8')

        with db.engine.begin() as conn:
            # 0) Idempotencia total: limpiar todo lo existente
            conn.exec_driver_sql("PRAGMA foreign_keys=OFF")

            from sqlalchemy import inspect as _insp
            insp = _insp(conn)
            # El inspector sobre la conexión activa lista todas las tablas
            for tbl in insp.get_table_names():
                conn.exec_driver_sql(f'DROP TABLE IF EXISTS "{tbl}"')

            # 1) Ejecutar TODO el schema de una vez con executescript (SQLite)
            raw = conn.connection  # conexión DB-API subyacente (sqlite3.Connection)
            raw.executescript(script)

            conn.exec_driver_sql("PRAGMA foreign_keys=ON")

        # 2) Verificación FATAL: la tabla 'roles' debe existir YA aquí
        inspector = inspect(db.engine)
        tables = set(inspector.get_table_names())
        assert 'roles' in tables, f"'roles' NO existe. Tablas actuales: {sorted(tables)}"
        assert 'users' in tables, f"'users' NO existe. Tablas actuales: {sorted(tables)}"
        assert 'user_roles' in tables, f"'user_roles' NO existe. Tablas actuales: {sorted(tables)}"

        # 3) Preparar automap con API moderna (NADA de reflect=True)
        Base.prepare(autoload_with=db.engine)

        # 3.1) Si automap no creó la clase 'user_roles', la mapeamos explícitamente
        if 'user_roles' not in Base.classes:
            from sqlalchemy import Table
            from sqlalchemy.orm import registry
            user_roles_tbl = Base.metadata.tables.get('user_roles')
            if user_roles_tbl is None:
                user_roles_tbl = Table('user_roles', Base.metadata, autoload_with=db.engine)

            mapper_reg = registry(metadata=Base.metadata)
            @mapper_reg.mapped
            class UserRole:
                __table__ = user_roles_tbl
                __tablename__ = 'user_roles'

            Base.classes.user_roles = UserRole

        # 4) Seed idempotente (merge) – ahora sí podemos pedir la clase a automap
        Role = get_table_class("roles")
        User = get_table_class("users")
        UserRole = get_table_class("user_roles")
        Cliente = get_table_class("clientes")
        Ticket = get_table_class("tickets")

        from sqlalchemy.orm import Session
        with Session(bind=db.engine) as s:
            # Crea roles y usuarios de prueba
            s.merge(Role(id=1, code='admin', descripcion='Administrador'))
            s.merge(Role(id=2, code='autonomo', descripcion='Autónomo'))
            s.merge(Role(id=3, code='oficina', descripcion='Oficina'))
            
            s.merge(User(id=1, username='admin', password_hash=generate_password_hash('password123')))
            s.merge(User(id=2, username='autonomo', password_hash=generate_password_hash('password123')))
            s.merge(User(id=3, username='oficina', password_hash=generate_password_hash('password123')))

            s.merge(UserRole(user_id=1, role_id=1))
            s.merge(UserRole(user_id=2, role_id=2))
            s.merge(UserRole(user_id=3, role_id=3))

            # Add clients and tickets for tests
            s.merge(Cliente(id=1, nombre='Test Client 1'))
            s.merge(Cliente(id=2, nombre='Test Client 2'))

            s.merge(Ticket(id=1, cliente_id=1, creado_por=1, titulo='Reparación A', estado='abierto', tipo='averia', estado_pago='Pendiente'))
            s.merge(Ticket(id=2, cliente_id=1, creado_por=1, titulo='Instalación B', estado='abierto', tipo='instalacion', estado_pago='Pendiente'))
            s.merge(Ticket(id=3, cliente_id=2, creado_por=1, titulo='Mantenimiento C', estado='abierto', tipo='mantenimiento', estado_pago='Pendiente'))
            s.merge(Ticket(id=4, cliente_id=2, creado_por=1, titulo='Reparación D', estado='en_progreso', tipo='averia', estado_pago='Pagado'))
            s.merge(Ticket(id=5, cliente_id=1, creado_por=1, titulo='Instalación E', estado='en_progreso', tipo='instalacion', estado_pago='Pagado'))
            s.merge(Ticket(id=6, cliente_id=2, creado_por=1, titulo='Revisión F', estado='finalizado', tipo='averia', estado_pago='Pagado'))
            s.merge(Ticket(id=7, cliente_id=1, creado_por=1, titulo='Mantenimiento G', estado='cancelado', tipo='mantenimiento', estado_pago='Pagado'))
            
            s.commit()

        yield app

@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def auth(client):
    class AuthActions:
        def login(self, username="admin", password="password123"):
            return client.post(
                "/auth/login", data={"username": username, "password": password}
            )

        def logout(self):
            return client.get("/auth/logout")

    return AuthActions()
