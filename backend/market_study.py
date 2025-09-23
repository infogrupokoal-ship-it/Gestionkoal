import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
import sqlite3

from backend.db import get_db
from backend.auth import login_required

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
    materials = db.execute('SELECT id, nombre FROM materiales ORDER BY nombre').fetchall()
    services = db.execute('SELECT id, name FROM services ORDER BY name').fetchall()
    freelancers = db.execute('SELECT u.id, u.username FROM users u JOIN freelancers f ON u.id = f.user_id ORDER BY u.username').fetchall()

    if request.method == 'POST':
        tipo_elemento = request.form.get('tipo_elemento')
        elemento_id = request.form.get('elemento_id', type=int)
        region = request.form.get('region')
        factor_dificultad = request.form.get('factor_dificultad', type=float, default=1.0)
        recargo_urgencia = request.form.get('recargo_urgencia', type=float, default=0.0)
        precio_recomendado = request.form.get('precio_recomendado', type=float)
        error = None

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

    materials = db.execute('SELECT id, nombre FROM materiales ORDER BY nombre').fetchall()
    services = db.execute('SELECT id, name FROM services ORDER BY name').fetchall()
    freelancers = db.execute('SELECT u.id, u.username FROM users u JOIN freelancers f ON u.id = f.user_id ORDER BY u.username').fetchall()

    if request.method == 'POST':
        tipo_elemento = request.form.get('tipo_elemento')
        elemento_id = request.form.get('elemento_id', type=int)
        region = request.form.get('region')
        factor_dificultad = request.form.get('factor_dificultad', type=float, default=1.0)
        recargo_urgencia = request.form.get('recargo_urgencia', type=float, default=0.0)
        precio_recomendado = request.form.get('precio_recomendado', type=float)
        error = None

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
