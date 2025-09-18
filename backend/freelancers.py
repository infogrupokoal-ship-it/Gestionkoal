import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
import sqlite3

from backend.db import get_db
from backend.auth import login_required

bp = Blueprint('freelancers', __name__, url_prefix='/freelancers')

@bp.route('/')
@login_required
def list_freelancers():
    db = get_db()
    freelancers = db.execute(
        '''
        SELECT
            u.id, u.username, u.email, u.telefono,
            f.category, f.specialty, f.city_province, f.web, f.notes, f.source_url,
            f.hourly_rate_normal, f.hourly_rate_tier2, f.hourly_rate_tier3, f.difficulty_surcharge_rate,
            GROUP_CONCAT(r.code) AS roles_codes
        FROM users u
        JOIN freelancers f ON u.id = f.user_id
        LEFT JOIN user_roles ur ON u.id = ur.user_id
        LEFT JOIN roles r ON ur.role_id = r.id
        WHERE u.role = "autonomo"
        GROUP BY u.id, u.username, u.email, u.telefono, f.category, f.specialty, f.city_province, f.web, f.notes, f.source_url, f.hourly_rate_normal, f.hourly_rate_tier2, f.hourly_rate_tier3, f.difficulty_surcharge_rate
        ORDER BY u.username
        '''
    ).fetchall()
    return render_template('freelancers/list.html', freelancers=freelancers)

@bp.route('/add', methods=('GET', 'POST'))
@login_required
def add_freelancer():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        telefono = request.form['telefono']
        password = request.form['password']
        
        category = request.form.get('category')
        specialty = request.form.get('specialty')
        city_province = request.form.get('city_province')
        web = request.form.get('web')
        notes = request.form.get('notes')
        source_url = request.form.get('source_url')
        hourly_rate_normal = request.form.get('hourly_rate_normal')
        hourly_rate_tier2 = request.form.get('hourly_rate_tier2')
        hourly_rate_tier3 = request.form.get('hourly_rate_tier3')
        difficulty_surcharge_rate = request.form.get('difficulty_surcharge_rate')

        db = get_db()
        error = None

        if not username:
            error = 'El nombre de usuario es obligatorio.'
        elif not password:
            error = 'La contraseña es obligatoria.'

        if error is not None:
            flash(error)
        else:
            try:
                from werkzeug.security import generate_password_hash
                cursor = db.execute(
                    'INSERT INTO users (username, email, telefono, password_hash, role) VALUES (?, ?, ?, ?, "autonomo")',
                    (username, email, telefono, generate_password_hash(password))
                )
                user_id = cursor.lastrowid

                db.execute(
                    '''
                    INSERT INTO freelancers (
                        user_id, category, specialty, city_province, web, notes, source_url,
                        hourly_rate_normal, hourly_rate_tier2, hourly_rate_tier3, difficulty_surcharge_rate
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        user_id, category, specialty, city_province, web, notes, source_url,
                        hourly_rate_normal, hourly_rate_tier2, hourly_rate_tier3, difficulty_surcharge_rate
                    )
                )
                db.commit()
                flash('¡Autónomo añadido correctamente!')
                return redirect(url_for('freelancers.list_freelancers'))
            except sqlite3.IntegrityError:
                error = f"El autónomo {username} ya existe."
            except Exception as e:
                error = f"Ocurrió un error inesperado: {e}"
            
            if error:
                flash(error)

    return render_template('freelancers/form.html')

@bp.route('/<int:freelancer_id>/edit', methods=('GET', 'POST'))
@login_required
def edit_freelancer(freelancer_id):
    db = get_db()
    freelancer = db.execute(
        '''
        SELECT
            u.id, u.username, u.email, u.telefono,
            f.category, f.specialty, f.city_province, f.web, f.notes, f.source_url,
            f.hourly_rate_normal, f.hourly_rate_tier2, f.hourly_rate_tier3, f.difficulty_surcharge_rate
        FROM users u
        JOIN freelancers f ON u.id = f.user_id
        WHERE u.id = ? AND u.role = "autonomo"
        ''',
        (freelancer_id,)
    ).fetchone()

    if freelancer is None:
        flash('Autónomo no encontrado.')
        return redirect(url_for('freelancers.list_freelancers'))

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        telefono = request.form['telefono']
        password = request.form['password'] # Optional password change

        category = request.form.get('category')
        specialty = request.form.get('specialty')
        city_province = request.form.get('city_province')
        web = request.form.get('web')
        notes = request.form.get('notes')
        source_url = request.form.get('source_url')
        hourly_rate_normal = request.form.get('hourly_rate_normal')
        hourly_rate_tier2 = request.form.get('hourly_rate_tier2')
        hourly_rate_tier3 = request.form.get('hourly_rate_tier3')
        difficulty_surcharge_rate = request.form.get('difficulty_surcharge_rate')

        error = None

        if not username:
            error = 'El nombre de usuario es obligatorio.'

        if error is not None:
            flash(error)
        else:
            try:
                if password:
                    from werkzeug.security import generate_password_hash
                    db.execute(
                        'UPDATE users SET username = ?, email = ?, telefono = ?, password_hash = ? WHERE id = ?',
                        (username, email, telefono, generate_password_hash(password), freelancer_id)
                    )
                else:
                    db.execute(
                        'UPDATE users SET username = ?, email = ?, telefono = ? WHERE id = ?',
                        (username, email, telefono, freelancer_id)
                    )
                
                db.execute(
                    '''
                    UPDATE freelancers SET
                        category = ?, specialty = ?, city_province = ?, web = ?, notes = ?, source_url = ?,
                        hourly_rate_normal = ?, hourly_rate_tier2 = ?, hourly_rate_tier3 = ?, difficulty_surcharge_rate = ?
                    WHERE user_id = ?
                    ''',
                    (
                        category, specialty, city_province, web, notes, source_url,
                        hourly_rate_normal, hourly_rate_tier2, hourly_rate_tier3, difficulty_surcharge_rate,
                        freelancer_id
                    )
                )
                db.commit()
                flash('¡Autónomo actualizado correctamente!')
                return redirect(url_for('freelancers.list_freelancers'))
            except sqlite3.IntegrityError:
                error = f"El autónomo {username} ya existe."
            except Exception as e:
                error = f"Ocurrió un error inesperado: {e}"
            
            if error:
                flash(error)

    return render_template('freelancers/form.html', freelancer=freelancer)
