from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from backend.auth import login_required
from backend.db import get_db

bp = Blueprint('freelancers', __name__, url_prefix='/freelancers')

@bp.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    # Fetch jobs assigned to the current logged-in freelancer
    assigned_jobs = db.execute(
        '''
        SELECT
            t.id, t.titulo, t.descripcion, t.estado, t.fecha_creacion, t.fecha_inicio,
            c.nombre AS client_name
        FROM tickets t
        JOIN clientes c ON t.cliente_id = c.id
        WHERE t.asignado_a = ?
        ORDER BY t.fecha_creacion DESC
        ''',
        (g.user.id,)
    ).fetchall()

    return render_template('freelancers/dashboard.html', assigned_jobs=assigned_jobs)

@bp.route('/')
@login_required
def list_freelancers():
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('index')) # Redirect to a safe page, e.g., index or login

    # freelancers = db.execute( # Removed unused variable
    #     """
    #     SELECT f.id, u.username, f.category, f.specialty, f.hourly_rate_normal
    #     FROM freelancers f
    #     JOIN users u ON f.user_id = u.id
    #     ORDER BY u.username
    #     """
    # ).fetchall()
    freelancers_data = db.execute(
        """
        SELECT f.id, u.username, f.category, f.specialty, f.hourly_rate_normal
        FROM freelancers f
        JOIN users u ON f.user_id = u.id
        ORDER BY u.username
        """
    ).fetchall()
    return render_template('freelancers/list.html', freelancers=freelancers_data)

@bp.route('/<int:freelancer_id>')
@login_required
def view_freelancer(freelancer_id):
    db = get_db()
    freelancer = db.execute(
        '''
        SELECT
            u.id, u.username, u.email, u.telefono,
            f.category, f.specialty, f.city_province, f.web, f.notes, f.source_url,
            f.hourly_rate_normal, f.hourly_rate_tier2, f.hourly_rate_tier3, f.difficulty_surcharge_rate, f.recargo_zona, f.recargo_dificultad
        FROM users u
        JOIN freelancers f ON u.id = f.user_id
        WHERE u.id = ? AND u.role = "autonomo"
        ''',
        (freelancer_id,)
    ).fetchone()

    if freelancer is None:
        flash('Autónomo no encontrado.', 'error')
        return redirect(url_for('freelancers.list_freelancers'))

    return render_template('freelancers/view.html', freelancer=freelancer)

@bp.route('/add', methods=('GET', 'POST'))
@login_required
def add_freelancer():
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('freelancers.list_freelancers'))

    if request.method == 'POST':
        user_id = request.form['user_id']
        category = request.form['category']
        specialty = request.form['specialty']
        hourly_rate_normal = request.form['hourly_rate_normal']
        error = None

        if not user_id or not category or not specialty or not hourly_rate_normal:
            error = 'User, Category, Specialty, and Hourly Rate are required.'

        if error is None:
            try:
                db.execute(
                    "INSERT INTO freelancers (user_id, category, specialty, hourly_rate_normal) VALUES (?, ?, ?, ?)",
                    (user_id, category, specialty, hourly_rate_normal),
                )
                db.commit()
                flash('Freelancer added successfully.', 'success')
                return redirect(url_for('freelancers.list_freelancers'))
            except db.IntegrityError:
                error = f"Freelancer with user ID {user_id} already exists."
                db.rollback()
            except Exception as e:
                error = f"An error occurred: {e}"
                db.rollback()

        flash(error)

    users = db.execute('SELECT id, username FROM users WHERE id NOT IN (SELECT user_id FROM freelancers)').fetchall()
    return render_template('freelancers/add.html', users=users)
@bp.route('/<int:freelancer_id>/edit', methods=('GET', 'POST'))
@login_required
def edit_freelancer(freelancer_id):
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('freelancers.list_freelancers'))

    freelancer = db.execute(
        """
        SELECT f.id, f.user_id, u.username, f.category, f.specialty, f.hourly_rate_normal
        FROM freelancers f
        JOIN users u ON f.user_id = u.id
        WHERE f.id = ?
        """,
        (freelancer_id,)
    ).fetchone()

    if freelancer is None:
        flash('Freelancer not found.', 'error')
        return redirect(url_for('freelancers.list_freelancers'))

    if request.method == 'POST':
        user_id = request.form['user_id']
        category = request.form['category']
        specialty = request.form['specialty']
        hourly_rate_normal = request.form['hourly_rate_normal']
        error = None

        if not user_id or not category or not specialty or not hourly_rate_normal:
            error = 'User, Category, Specialty, and Hourly Rate are required.'

        if error is None:
            try:
                db.execute(
                    "UPDATE freelancers SET user_id = ?, category = ?, specialty = ?, hourly_rate_normal = ? WHERE id = ?",
                    (user_id, category, specialty, hourly_rate_normal, freelancer_id),
                )
                db.commit()
                flash('Freelancer updated successfully.', 'success')
                return redirect(url_for('freelancers.list_freelancers'))
            except db.IntegrityError:
                error = f"Freelancer with user ID {user_id} already exists."
                db.rollback()
            except Exception as e:
                error = f"An error occurred: {e}"
                db.rollback()

        flash(error)

    users = db.execute('SELECT id, username FROM users').fetchall()
    return render_template('freelancers/edit.html', freelancer=freelancer, users=users)

@bp.route('/<int:freelancer_id>/delete', methods=('POST',))
@login_required
def delete_freelancer(freelancer_id):
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('freelancers.list_freelancers'))

    try:
        db.execute('DELETE FROM freelancers WHERE id = ?', (freelancer_id,))
        db.commit()
        flash('Freelancer deleted successfully.', 'success')
    except Exception as e:
        flash(f'Error deleting freelancer: {e}', 'error')
        db.rollback()

    return redirect(url_for('freelancers.list_freelancers'))