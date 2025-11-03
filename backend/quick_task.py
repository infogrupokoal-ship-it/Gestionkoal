from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from backend.extensions import db
from backend.models import get_table_class
from backend.auth import permission_required

quick_task_bp = Blueprint('quick_task', __name__, url_prefix='/quick_task')

@quick_task_bp.route('/add', methods=['GET', 'POST'])
@login_required
@permission_required('create_quick_task') # Asumiendo un permiso para crear tareas rápidas
def add_quick_task():
    Ticket = get_table_class('tickets')
    Client = get_table_class('clientes')
    User = get_table_class('users')

    if request.method == 'POST':
        descripcion = request.form.get('descripcion')
        asignado_a_id = request.form.get('asignado_a')
        urgencia = request.form.get('urgencia')
        cliente_id = request.form.get('cliente_id')

        if not descripcion:
            flash('La descripción de la tarea es obligatoria.', 'error')
            return redirect(url_for('quick_task.add_quick_task'))

        try:
            new_task = Ticket(
                titulo=descripcion, # Usamos la descripción como título
                descripcion=descripcion,
                tipo='tarea_rapida',
                estado='pendiente',
                prioridad=urgencia,
                creado_por=current_user.id,
                cliente_id=cliente_id if cliente_id else None,
                asignado_a=asignado_a_id if asignado_a_id else None,
                # Otros campos pueden ser nulos o tener valores por defecto
            )
            db.session.add(new_task)
            db.session.commit()
            flash('Tarea rápida creada con éxito.', 'success')
            return redirect(url_for('index')) # Redirigir al dashboard o a la lista de tareas
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear la tarea rápida: {e}', 'error')

    clientes = Client.query.all()
    freelancers = User.query.filter_by(role='autonomo').all()
    return render_template('quick_task/form.html', clientes=clientes, freelancers=freelancers)