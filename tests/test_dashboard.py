import pytest

from backend import create_app, db
from backend.models import Base, session_scope, get_table_class, _prepare_mappings
from werkzeug.security import generate_password_hash


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['DATABASE'] = ':memory:' # Use in-memory SQLite for testing
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app_context():
        # Create all tables based on SQLAlchemy models
        Base.metadata.create_all(db.engine)
        # Ensure automap_base reflects the newly created tables
        _prepare_mappings()

        # Seed test data using SQLAlchemy session
        with session_scope() as session:
            # Get automapped classes
            Cliente = get_table_class("clientes")
            User = get_table_class("users")
            Ticket = get_table_class("tickets")
            Role = get_table_class("roles")
            UserRole = get_table_class("user_roles")

            # Seed Roles (if not already seeded by init-db, though tests should be isolated)
            if not session.query(Role).filter_by(code='admin').first():
                admin_role = Role(code='admin', descripcion='Administrador')
                session.add(admin_role)
            if not session.query(Role).filter_by(code='autonomo').first():
                autonomo_role = Role(code='autonomo', descripcion='Autónomo')
                session.add(autonomo_role)
            if not session.query(Role).filter_by(code='oficina').first():
                oficina_role = Role(code='oficina', descripcion='Oficina')
                session.add(oficina_role)
            session.commit() # Commit roles before users to get their IDs

            # Seed Users
            admin_user = User(id=1, username='admin', password_hash=generate_password_hash('password123'), role='admin')
            autonomo_user = User(id=2, username='autonomo', password_hash=generate_password_hash('password123'), role='autonomo')
            oficina_user = User(id=3, username='oficina', password_hash=generate_password_hash('password123'), role='oficina')
            session.add_all([admin_user, autonomo_user, oficina_user])
            session.commit() # Commit users to get their IDs

            # Link users to roles
            admin_role_obj = session.query(Role).filter_by(code='admin').first()
            autonomo_role_obj = session.query(Role).filter_by(code='autonomo').first()
            oficina_role_obj = session.query(Role).filter_by(code='oficina').first()

            session.add(UserRole(user_id=admin_user.id, role_id=admin_role_obj.id))
            session.add(UserRole(user_id=autonomo_user.id, role_id=autonomo_role_obj.id))
            session.add(UserRole(user_id=oficina_user.id, role_id=oficina_role_obj.id))
            session.commit()

            # Seed Clientes
            cliente1 = Cliente(id=1, nombre='Cliente Test 1')
            cliente2 = Cliente(id=2, nombre='Cliente Test 2')
            session.add_all([cliente1, cliente2])
            session.commit()

            # Seed Tickets
            session.add(Ticket(id=1, cliente_id=1, descripcion='Reparación A', estado='abierto', estado_pago='Pendiente', creado_por=1))
            session.add(Ticket(id=2, cliente_id=1, descripcion='Mantenimiento B', estado='en_progreso', estado_pago='Pagado', creado_por=1))
            session.add(Ticket(id=3, cliente_id=2, descripcion='Instalación C', estado='abierto', estado_pago='Pendiente', creado_por=2))
            session.add(Ticket(id=4, cliente_id=2, descripcion='Revisión D', estado='completado', estado_pago='Pagado', creado_por=2))
            session.add(Ticket(id=5, cliente_id=1, descripcion='Urgencia E', estado='abierto', estado_pago='Parcialmente Pagado', creado_por=1))
            session.commit()

    yield app

    with app.app_context():
        # Clean up after tests
        Base.metadata.drop_all(db.engine)

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth(client):
    class AuthActions:
        def login(self, username='admin', password='password123'):
            return client.post('/auth/login', data={'username': username, 'password': password})

        def logout(self):
            return client.get('/auth/logout')

    return AuthActions()

def test_dashboard_kpis(client, auth):
    auth.login()
    response = client.get('/')
    assert response.status_code == 200

    # Check total tickets
    assert b'<div class="stat-number">5</div>\n            <div>Total Trabajos</div>' in response.data

    # Check pending tickets (estado = 'abierto')
    assert b'<div class="stat-number">3</div>\n            <div>Trabajos Pendientes</div>' in response.data

    # Check pending payments (estado_pago != 'Pagado')
    assert b'<div class="stat-number">3</div>\n            <div>Pagos Pendientes</div>' in response.data

    # Check total clients
    assert b'<div class="stat-number">2</div>\n            <div>Total Clientes</div>' in response.data

    # Check recent tickets table (example for one ticket)
    assert b'<td>Reparaci\xc3\xb3n A</td>' in response.data
    assert b'<td>Cliente Test 1</td>' in response.data
    assert b'<td>abierto</td>' in response.data
