import pytest
from backend import create_app
from backend.db import get_db

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['DATABASE'] = ':memory:' # Use in-memory SQLite for testing

    with app.app_context():
        db = get_db()
        # Initialize schema
        with app.open_resource('schema.sql') as f:
            db.executescript(f.read().decode('utf8'))

        # Seed test data
        db.execute("INSERT INTO clientes (id, nombre) VALUES (?, ?)", (1, 'Cliente Test 1'))
        db.execute("INSERT INTO clientes (id, nombre) VALUES (?, ?)", (2, 'Cliente Test 2'))
        db.execute("INSERT INTO users (id, username, password_hash, role) VALUES (?, ?, ?, ?)", (1, 'admin', 'pbkdf2:sha256:150000$test$test', 'admin'))
        db.execute("INSERT INTO users (id, username, password_hash, role) VALUES (?, ?, ?, ?)", (2, 'autonomo', 'pbkdf2:sha256:150000$test$test', 'autonomo'))
        db.execute("INSERT INTO users (id, username, password_hash, role) VALUES (?, ?, ?, ?)", (3, 'oficina', 'pbkdf2:sha256:150000$test$test', 'oficina'))

        # Test Tickets
        db.execute("INSERT INTO tickets (id, cliente_id, descripcion, estado, estado_pago, creado_por) VALUES (?, ?, ?, ?, ?, ?)", (1, 1, 'Reparación A', 'abierto', 'Pendiente', 1))
        db.execute("INSERT INTO tickets (id, cliente_id, descripcion, estado, estado_pago, creado_por) VALUES (?, ?, ?, ?, ?, ?)", (2, 1, 'Mantenimiento B', 'en_progreso', 'Pagado', 1))
        db.execute("INSERT INTO tickets (id, cliente_id, descripcion, estado, estado_pago, creado_por) VALUES (?, ?, ?, ?, ?, ?)", (3, 2, 'Instalación C', 'abierto', 'Pendiente', 2))
        db.execute("INSERT INTO tickets (id, cliente_id, descripcion, estado, estado_pago, creado_por) VALUES (?, ?, ?, ?, ?, ?)", (4, 2, 'Revisión D', 'completado', 'Pagado', 2))
        db.execute("INSERT INTO tickets (id, cliente_id, descripcion, estado, estado_pago, creado_por) VALUES (?, ?, ?, ?, ?, ?)", (5, 1, 'Urgencia E', 'abierto', 'Parcialmente Pagado', 1))

        db.commit()

    yield app

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
