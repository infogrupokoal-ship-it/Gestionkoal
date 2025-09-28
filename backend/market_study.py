import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
import sqlite3

from backend.db import get_db
from backend.auth import login_required
from backend.forms import get_material_choices, get_service_choices, get_freelancer_choices # New imports

bp = Blueprint('market_study', __name__, url_prefix='/market_study')

@bp.route('/')
@login_required
def list_market_studies():
    db = get_db()
    studies = db.execute(
        'SELECT id, tipo_elemento, elemento_id, region, factor_dificultad, recargo_urgencia, precio_recomendado, fecha_estudio FROM estudio_mercado ORDER BY fecha_estudio DESC'
    ).fetchall()
    return render_template('market_study/list.html', studies=studies)

@bp.route('/add', methods=('GET', 'POST'))
@login_required
def add_market_study():
    db = get_db()
    materials = get_material_choices() # Refactored
    services = get_service_choices() # Refactored
    freelancers = get_freelancer_choices() # Refactored

    if request.method == 'POST':
        error = None
        try:
            tipo_elemento = request.form.get('tipo_elemento')
            elemento_id = request.form.get('elemento_id', type=int)
            region = request.form.get('region')

            # Handle comma as decimal separator
            factor_dificultad_str = request.form.get('factor_dificultad', '1.0').replace(',', '.')
            recargo_urgencia_str = request.form.get('recargo_urgencia', '0.0').replace(',', '.')
            precio_recomendado_str = request.form.get('precio_recomendado', '').replace(',', '.')

            factor_dificultad = float(factor_dificultad_str) if factor_dificultad_str else 1.0
            recargo_urgencia = float(recargo_urgencia_str) if recargo_urgencia_str else 0.0
            precio_recomendado = float(precio_recomendado_str) if precio_recomendado_str else None

        except (ValueError, TypeError):
            error = "Valores numéricos inválidos. Por favor use '.' o ',' como separador decimal."

        if not tipo_elemento or not elemento_id or not precio_recomendado:
            error = 'Tipo de elemento, elemento y precio recomendado son obligatorios.'

        if error is not None:
            flash(error)
        else:
            try:
                db.execute(
                    '''INSERT INTO estudio_mercado (tipo_elemento, elemento_id, region, factor_dificultad, recargo_urgencia, precio_recomendado)
                       VALUES (?, ?, ?, ?, ?, ?)''',
                    (tipo_elemento, elemento_id, region, factor_dificultad, recargo_urgencia, precio_recomendado)
                )
                db.commit()
                flash('¡Estudio de mercado añadido correctamente!')
                return redirect(url_for('market_study.list_market_studies'))
            except Exception as e:
                flash(f'Ocurrió un error inesperado: {e}', 'error')
                db.rollback()

    return render_template('market_study/form.html', study=None, materials=materials, services=services, freelancers=freelancers)

@bp.route('/<int:study_id>/edit', methods=('GET', 'POST'))
@login_required
def edit_market_study(study_id):
    db = get_db()
    study = db.execute('SELECT * FROM estudio_mercado WHERE id = ?', (study_id,)).fetchone()

    if study is None:
        flash('Estudio de mercado no encontrado.')
        return redirect(url_for('market_study.list_market_studies'))

    materials = get_material_choices() # Refactored
    services = get_service_choices() # Refactored
    freelancers = get_freelancer_choices() # Refactored

    if request.method == 'POST':
        error = None
        try:
            tipo_elemento = request.form.get('tipo_elemento')
            elemento_id = request.form.get('elemento_id', type=int)
            region = request.form.get('region')

            # Handle comma as decimal separator
            factor_dificultad_str = request.form.get('factor_dificultad', '1.0').replace(',', '.')
            recargo_urgencia_str = request.form.get('recargo_urgencia', '0.0').replace(',', '.')
            precio_recomendado_str = request.form.get('precio_recomendado', '').replace(',', '.')

            factor_dificultad = float(factor_dificultad_str) if factor_dificultad_str else 1.0
            recargo_urgencia = float(recargo_urgencia_str) if recargo_urgencia_str else 0.0
            precio_recomendado = float(precio_recomendado_str) if precio_recomendado_str else None

        except (ValueError, TypeError):
            error = "Valores numéricos inválidos. Por favor use '.' o ',' como separador decimal."


        if not tipo_elemento or not elemento_id or not precio_recomendado:
            error = 'Tipo de elemento, elemento y precio recomendado son obligatorios.'

        if error is not None:
            flash(error)
        else:
            try:
                db.execute(
                    '''UPDATE estudio_mercado SET 
                       tipo_elemento = ?, elemento_id = ?, region = ?, factor_dificultad = ?, 
                       recargo_urgencia = ?, precio_recomendado = ?
                       WHERE id = ?''',
                    (tipo_elemento, elemento_id, region, factor_dificultad, recargo_urgencia, precio_recomendado, study_id)
                )
                db.commit()
                flash('¡Estudio de mercado actualizado correctamente!')
                return redirect(url_for('market_study.list_market_studies'))
            except Exception as e:
                flash(f'Ocurrió un error inesperado: {e}', 'error')
                db.rollback()

    return render_template('market_study/form.html', study=study, materials=materials, services=services, freelancers=freelancers)

@bp.route('/<int:study_id>/delete', methods=('POST',))
@login_required
def delete_market_study(study_id):
    db = get_db()
    db.execute('DELETE FROM estudio_mercado WHERE id = ?', (study_id,))
    db.commit()
    flash('¡Estudio de mercado eliminado correctamente!')
    return redirect(url_for('market_study.list_market_studies'))

