import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
import sqlite3

from backend.db import get_db

bp = Blueprint('catalog', __name__, url_prefix='/catalog')

@bp.route('/')
def list_catalog_items():
    db = get_db()
    services = db.execute(
        'SELECT id, name, description, price, recommended_price, category FROM services ORDER BY name'
    ).fetchall()
    materials = db.execute(
        'SELECT id, nombre, categoria, precio_venta_sugerido FROM materiales ORDER BY nombre'
    ).fetchall()
    return render_template('catalog/public_list.html', services=services, materials=materials)
