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
        'SELECT id, username, email, telefono FROM users WHERE role = "autonomo" ORDER BY username'
    ).fetchall()
    return render_template('freelancers/list.html', freelancers=freelancers)

@bp.route('/add', methods=('GET', 'POST'))
@login_required
def add_freelancer():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        phone_number = request.form['phone_number']
        password = request.form['password']
        db = get_db()
        error = None

        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'

        if error is not None:
            flash(error)
        else:
            try:
                from werkzeug.security import generate_password_hash
                db.execute(
                    'INSERT INTO users (username, email, phone_number, password_hash, role) VALUES (?, ?, ?, ?, "autonomo")',
                    (username, email, phone_number, generate_password_hash(password))
                )
                db.commit()
                flash('Freelancer added successfully!')
                return redirect(url_for('freelancers.list_freelancers'))
            except sqlite3.IntegrityError:
                error = f"Freelancer {username} already exists."
            except Exception as e:
                error = f"An unexpected error occurred: {e}"
            
            if error:
                flash(error)

    return render_template('freelancers/form.html')

@bp.route('/<int:freelancer_id>/edit', methods=('GET', 'POST'))
@login_required
def edit_freelancer(freelancer_id):
    db = get_db()
    freelancer = db.execute('SELECT id, username, email, phone_number FROM users WHERE id = ? AND role = "autonomo" ', (freelancer_id,)).fetchone()

    if freelancer is None:
        flash('Freelancer not found.')
        return redirect(url_for('freelancers.list_freelancers'))

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        phone_number = request.form['phone_number']
        password = request.form['password'] # Optional password change
        error = None

        if not username:
            error = 'Username is required.'

        if error is not None:
            flash(error)
        else:
            try:
                if password:
                    from werkzeug.security import generate_password_hash
                    db.execute(
                        'UPDATE users SET username = ?, email = ?, phone_number = ?, password_hash = ? WHERE id = ?',
                        (username, email, phone_number, generate_password_hash(password), freelancer_id)
                    )
                else:
                    db.execute(
                        'UPDATE users SET username = ?, email = ?, phone_number = ? WHERE id = ?',
                        (username, email, phone_number, freelancer_id)
                    )
                db.commit()
                flash('Freelancer updated successfully!')
                return redirect(url_for('freelancers.list_freelancers'))
            except sqlite3.IntegrityError:
                error = f"Freelancer {username} already exists."
            except Exception as e:
                error = f"An unexpected error occurred: {e}"
            
            if error:
                flash(error)

    return render_template('freelancers/form.html', freelancer=freelancer)
