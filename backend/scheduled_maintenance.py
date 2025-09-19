import functools
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
import sqlite3
from backend.db import get_db
from backend.auth import login_required
from datetime import datetime, timedelta

bp = Blueprint('scheduled_maintenance', __name__, url_prefix='/mantenimientos')

@bp.route('/')
@login_required
def list_maintenances():
    db = get_db()
    maintenances = db.execute(
        '''SELECT 
            mp.id, mp.tipo_mantenimiento, mp.proxima_fecha_mantenimiento, mp.estado, mp.descripcion,
            c.nombre AS cliente_nombre, e.marca AS equipo_marca, e.modelo AS equipo_modelo
        FROM mantenimientos_programados mp
        JOIN clientes c ON mp.cliente_id = c.id
        LEFT JOIN equipos e ON mp.equipo_id = e.id
        ORDER BY mp.proxima_fecha_mantenimiento DESC'''
    ).fetchall()
    return render_template('mantenimientos_programados/list.html', maintenances=maintenances)

@bp.route('/add', methods=('GET', 'POST'))
@login_required
def add_maintenance():
    db = get_db()
    clients = db.execute('SELECT id, nombre FROM clientes ORDER BY nombre').fetchall()
    equipos = db.execute('SELECT id, marca, modelo FROM equipos ORDER BY marca, modelo').fetchall()

    if request.method == 'POST':
        cliente_id = request.form.get('cliente_id')
        equipo_id = request.form.get('equipo_id')
        tipo_mantenimiento = request.form.get('tipo_mantenimiento')
        proxima_fecha_mantenimiento = request.form.get('proxima_fecha_mantenimiento')
        descripcion = request.form.get('descripcion')
        creado_por = g.user.id

        error = None
        if not cliente_id or not tipo_mantenimiento or not proxima_fecha_mantenimiento:
            error = 'Cliente, Tipo de Mantenimiento y Próxima Fecha son obligatorios.'

        if error is not None:
            flash(error)
        else:
            try:
                db.execute(
                    '''INSERT INTO mantenimientos_programados 
                       (cliente_id, equipo_id, tipo_mantenimiento, proxima_fecha_mantenimiento, descripcion, creado_por)
                       VALUES (?, ?, ?, ?, ?, ?)''',
                    (cliente_id, equipo_id if equipo_id else None, tipo_mantenimiento, proxima_fecha_mantenimiento, descripcion, creado_por)
                )
                db.commit()
                flash('¡Mantenimiento programado añadido correctamente!')
                return redirect(url_for('scheduled_maintenance.list_maintenances'))
            except Exception as e:
                db.rollback()
                error = f"Ocurrió un error al añadir el mantenimiento programado: {e}"
                flash(error)

    return render_template('mantenimientos_programados/form.html', title="Añadir Mantenimiento Programado", clients=clients, equipos=equipos)

@bp.route('/<int:maintenance_id>/edit', methods=('GET', 'POST'))
@login_required
def edit_maintenance(maintenance_id):
    db = get_db()
    maintenance = db.execute('SELECT * FROM mantenimientos_programados WHERE id = ?', (maintenance_id,)).fetchone()

    if maintenance is None:
        flash('Mantenimiento programado no encontrado.')
        return redirect(url_for('scheduled_maintenance.list_maintenances'))

    clients = db.execute('SELECT id, nombre FROM clientes ORDER BY nombre').fetchall()
    equipos = db.execute('SELECT id, marca, modelo FROM equipos ORDER BY marca, modelo').fetchall()

    if request.method == 'POST':
        cliente_id = request.form.get('cliente_id')
        equipo_id = request.form.get('equipo_id')
        tipo_mantenimiento = request.form.get('tipo_mantenimiento')
        proxima_fecha_mantenimiento = request.form.get('proxima_fecha_mantenimiento')
        descripcion = request.form.get('descripcion')
        estado = request.form.get('estado')

        error = None
        if not cliente_id or not tipo_mantenimiento or not proxima_fecha_mantenimiento:
            error = 'Cliente, Tipo de Mantenimiento y Próxima Fecha son obligatorios.'

        if error is not None:
            flash(error)
        else:
            try:
                db.execute(
                    '''UPDATE mantenimientos_programados SET 
                       cliente_id = ?, equipo_id = ?, tipo_mantenimiento = ?, 
                       proxima_fecha_mantenimiento = ?, descripcion = ?, estado = ?
                       WHERE id = ?''',
                    (cliente_id, equipo_id if equipo_id else None, tipo_mantenimiento, 
                     proxima_fecha_mantenimiento, descripcion, estado, maintenance_id)
                )
                db.commit()
                flash('¡Mantenimiento programado actualizado correctamente!')
                return redirect(url_for('scheduled_maintenance.list_maintenances'))
            except Exception as e:
                db.rollback()
                error = f"Ocurrió un error al actualizar el mantenimiento programado: {e}"
                flash(error)

    return render_template('mantenimientos_programados/form.html', title="Editar Mantenimiento Programado", maintenance=maintenance, clients=clients, equipos=equipos)

@bp.route('/generate_tickets_manual', methods=('GET', 'POST'))
@login_required
def generate_tickets_manual():
    db = get_db()
    # Fetch maintenances due today or in the past
    today = datetime.now().strftime('%Y-%m-%d')
    due_maintenances = db.execute(
        '''SELECT mp.id, mp.cliente_id, mp.equipo_id, mp.tipo_mantenimiento, mp.descripcion, mp.creado_por
           FROM mantenimientos_programados mp
           WHERE mp.proxima_fecha_mantenimiento <= ? AND mp.estado = 'activo'''
        , (today,)
    ).fetchall()

    generated_count = 0
    for maintenance in due_maintenances:
        try:
            # Create a new ticket for the due maintenance
            db.execute(
                '''INSERT INTO tickets (cliente_id, equipo_id, tipo, descripcion, estado, creado_por)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (maintenance['cliente_id'], maintenance['equipo_id'], 
                 f"Mantenimiento Programado: {maintenance['tipo_mantenimiento']}", 
                 maintenance['descripcion'] or f"Mantenimiento programado para {maintenance['tipo_mantenimiento']}",
                 'Pendiente', maintenance['creado_por'])
            )
            # Update the next scheduled date for the maintenance (e.g., add 1 month, 3 months, 1 year)
            # This is a simplified example, real logic would be more complex based on tipo_mantenimiento
            current_date = datetime.strptime(maintenance['proxima_fecha_mantenimiento'], '%Y-%m-%d')
            if maintenance['tipo_mantenimiento'] == 'mensual':
                next_date = current_date + timedelta(days=30) # Approx 1 month
            elif maintenance['tipo_mantenimiento'] == 'trimestral':
                next_date = current_date + timedelta(days=90) # Approx 3 months
            elif maintenance['tipo_mantenimiento'] == 'anual':
                next_date = current_date + timedelta(days=365) # Approx 1 year
            else:
                next_date = current_date + timedelta(days=7) # Default to 1 week if type unknown
            
            db.execute(
                'UPDATE mantenimientos_programados SET proxima_fecha_mantenimiento = ? WHERE id = ?',
                (next_date.strftime('%Y-%m-%d'), maintenance['id'])
            )
            generated_count += 1
        except Exception as e:
            db.rollback()
            flash(f"Error al generar ticket para mantenimiento {maintenance['id']}: {e}")
            return redirect(url_for('scheduled_maintenance.list_maintenances'))
    
    db.commit()
    flash(f'Se generaron {generated_count} tickets de mantenimiento.')
    return redirect(url_for('scheduled_maintenance.list_maintenances'))
