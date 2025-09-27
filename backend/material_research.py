import functools
import json

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from flask_login import login_required

from backend.db import get_db
from backend.auth import login_required

bp = Blueprint('material_research', __name__, url_prefix='/material_research')

@bp.route('/', methods=('GET', 'POST'))
@login_required
def research_form():
    materials = []
    db = get_db()
    if db:
        materials = db.execute('SELECT id, nombre FROM materiales ORDER BY nombre').fetchall()

    search_results = []
    if request.method == 'POST':
        material_id = request.form.get('material_id')
        search_query = request.form.get('search_query')
        source_name = request.form.get('source_name')
        source_url = request.form.get('source_url')
        price = request.form.get('price', type=float)

        if 'search_web' in request.form: # User clicked 'Search Web'
            flash('La búsqueda web no está implementada en esta versión.', 'warning')
            # The original code was architecturally incorrect and has been disabled.

        elif 'save_price' in request.form: # User clicked 'Save Price'
            if not material_id or not price:
                flash('Material and Price are required to save.', 'warning')
            else:
                try:
                    db.execute(
                        "INSERT INTO material_precios_externos (material_id, source_name, source_url, price) VALUES (?, ?, ?, ?)",
                        (material_id, source_name, source_url, price)
                    )
                    db.commit()
                    flash('Price saved successfully!', 'success')
                    return redirect(url_for('material_research.research_form'))
                except Exception as e:
                    flash(f'Error saving price: {e}', 'error')
                    db.rollback()

    return render_template('material_research/form.html', materials=materials, search_results=search_results)
