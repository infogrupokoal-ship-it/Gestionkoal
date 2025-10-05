# backend/forms.py

from backend.db import get_db


def get_client_choices():
    """Fetches a list of clients for use in form dropdowns."""
    db = get_db()
    return db.execute('SELECT id, nombre FROM clientes ORDER BY nombre').fetchall()

def get_freelancer_choices():
    """Fetches a list of users with the 'autonomo' role for dropdowns."""
    db = get_db()
    # Assuming 'autonomo' is the correct role code
    return db.execute("SELECT id, username FROM users WHERE role = 'autonomo' ORDER BY username").fetchall()

def get_technician_choices():
    """Fetches a list of technicians and similar roles for assignments."""
    db = get_db()
    return db.execute("SELECT id, username FROM users WHERE role IN ('tecnico', 'autonomo', 'admin') ORDER BY username").fetchall()

def get_material_choices():
    """Fetches a list of materials for form dropdowns."""
    db = get_db()
    return db.execute('SELECT id, nombre FROM materiales ORDER BY nombre').fetchall()

def get_service_choices():
    """Fetches a list of services for form dropdowns."""
    db = get_db()
    return db.execute('SELECT id, name FROM services ORDER BY name').fetchall()

def get_user_choices():
    """Fetches a list of all users for form dropdowns."""
    db = get_db()
    return db.execute('SELECT id, username FROM users ORDER BY username').fetchall()

def get_role_choices():
    """Fetches a list of all roles for form dropdowns."""
    db = get_db()
    return db.execute('SELECT id, code, descripcion FROM roles ORDER BY code').fetchall()
