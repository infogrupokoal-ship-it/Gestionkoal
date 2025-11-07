from datetime import datetime

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from backend.extensions import db
from backend.models import get_table_class
from backend.whatsapp import WhatsAppClient  # Importar WhatsAppClient

# from backend.utils.email_utils import send_email # Descomentar si se implementa el envío de email

price_requests_bp = Blueprint('price_requests', __name__, url_prefix='/solicitudes-precio')

@price_requests_bp.route('/')
@login_required
def list_price_requests():
    if not current_user.has_permission('view_price_requests'):
        flash('No tienes permiso para ver las solicitudes de precio.', 'error')
        return redirect(url_for('index'))

    PriceRequest = get_table_class('price_requests')
    requests = db.session.query(PriceRequest).order_by(PriceRequest.fecha.desc()).all()
    return render_template('price_requests/list.html', requests=requests)

@price_requests_bp.route('/nueva', methods=['GET', 'POST'])
@login_required
def new_price_request():
    if not current_user.has_permission('create_price_requests'):
        flash('No tienes permiso para crear solicitudes de precio.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        comentarios = request.form.get('comentarios')

        try:
            PriceRequest = get_table_class('price_requests')
            new_request = PriceRequest(
                creado_por=current_user.id,
                comentarios=comentarios,
                estado='borrador'
            )
            db.session.add(new_request)
            db.session.commit()
            flash('Solicitud de precio creada con éxito.', 'success')
            return redirect(url_for('price_requests.edit_price_request', id=new_request.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear la solicitud de precio: {e}', 'error')

    return render_template('price_requests/form.html')

@price_requests_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def edit_price_request(id):
    if not current_user.has_permission('edit_price_requests'):
        flash('No tienes permiso para editar solicitudes de precio.', 'error')
        return redirect(url_for('index'))

    PriceRequest = get_table_class('price_requests')
    PriceRequestItem = get_table_class('price_request_items')
    Material = get_table_class('materiales')
    Service = get_table_class('servicios')

    request_obj = db.session.query(PriceRequest).filter_by(id=id).first_or_404()

    if request.method == 'POST':
        # Lógica para añadir materiales/servicios a la solicitud
        material_id = request.form.get('material_id')
        service_id = request.form.get('service_id')
        cantidad = request.form.get('cantidad', type=float)
        unidad = request.form.get('unidad')
        observaciones = request.form.get('observaciones')

        if not cantidad or cantidad <= 0:
            flash('La cantidad debe ser un número positivo.', 'error')
        elif not (material_id or service_id):
            flash('Debe seleccionar un material o un servicio.', 'error')
        else:
            try:
                new_item = PriceRequestItem(
                    request_id=request_obj.id,
                    material_id=material_id if material_id else None,
                    service_id=service_id if service_id else None,
                    cantidad=cantidad,
                    unidad=unidad,
                    observaciones=observaciones
                )
                db.session.add(new_item)
                db.session.commit()
                flash('Artículo añadido a la solicitud.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error al añadir artículo: {e}', 'error')
        return redirect(url_for('price_requests.edit_price_request', id=id))

    items = db.session.query(PriceRequestItem).filter_by(request_id=id).all()
    materials = db.session.query(Material).all()
    services = db.session.query(Service).all()

    return render_template('price_requests/edit.html', request=request_obj, items=items, materials=materials, services=services)

@price_requests_bp.route('/<int:id>/enviar', methods=['POST'])
@login_required
def send_price_request(id):
    if not current_user.has_permission('send_price_requests'):
        flash('No tienes permiso para enviar solicitudes de precio.', 'error')
        return redirect(url_for('index'))

    PriceRequest = get_table_class('price_requests')
    PriceRequestItem = get_table_class('price_request_items')
    PriceRequestProvider = get_table_class('price_request_providers')
    Material = get_table_class('materiales')
    Service = get_table_class('servicios')
    Provider = get_table_class('providers')

    request_obj = db.session.query(PriceRequest).filter_by(id=id).first_or_404()

    # Obtener los items de la solicitud
    request_items = db.session.query(PriceRequestItem).filter_by(request_id=id).all()

    # Obtener los proveedores asociados a esta solicitud
    request_providers = db.session.query(PriceRequestProvider).filter_by(request_id=id).all()

    if not request_providers:
        flash('No hay proveedores seleccionados para esta solicitud.', 'error')
        return redirect(url_for('price_requests.edit_price_request', id=id))

    whatsapp_client = WhatsAppClient()

    # Construir el mensaje de la solicitud
    message_body = f"¡Hola! Tenemos una solicitud de precios para ti (Solicitud #{request_obj.id}).\n\n"
    message_body += "Artículos solicitados:\n"
    for item in request_items:
        item_name = ""
        if item.material_id:
            material = db.session.query(Material).filter_by(id=item.material_id).first()
            if material:
                item_name = material.nombre
        elif item.service_id:
            service = db.session.query(Service).filter_by(id=item.service_id).first()
            if service:
                item_name = service.nombre

        message_body += f"- {item.cantidad} {item.unidad} de {item_name} ({item.observaciones or ''})\n"

    message_body += f"\nPor favor, envíanos tu mejor cotización y plazo de entrega. Puedes registrar tu cotización en el siguiente enlace: {url_for('price_requests.register_provider_quote', id=request_obj.id, provider_id='[PROVIDER_ID_PLACEHOLDER]', _external=True)}\n"
    message_body += "\n¡Gracias!"

    try:
        for rp in request_providers:
            provider = db.session.query(Provider).filter_by(id=rp.proveedor_id).first()
            if not provider:
                continue

            # Reemplazar el placeholder del ID del proveedor en el enlace
            provider_specific_message = message_body.replace('[PROVIDER_ID_PLACEHOLDER]', str(provider.id))

            # Enviar por WhatsApp
            if provider.whatsapp_number:
                whatsapp_client.send_text(provider.whatsapp_number, provider_specific_message)
                rp.estado_envio = 'enviado_whatsapp'
                rp.medio_envio = 'whatsapp'
                rp.contacto = provider.whatsapp_number
                flash(f'Solicitud enviada a {provider.nombre} por WhatsApp.', 'success')
            elif provider.email:
                # Simular envío de email
                # send_email(provider.email, f"Solicitud de Precios #{request_obj.id}", provider_specific_message)
                current_app.logger.info(f"Simulando envío de email a {provider.email} con mensaje: {provider_specific_message}")
                rp.estado_envio = 'enviado_email'
                rp.medio_envio = 'email'
                rp.contacto = provider.email
                flash(f'Solicitud enviada a {provider.nombre} por Email (simulado). ', 'success')
            else:
                rp.estado_envio = 'sin_contacto'
                flash(f'No se pudo enviar la solicitud a {provider.nombre}: no hay número de WhatsApp ni email.', 'warning')

            rp.fecha_envio = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            db.session.add(rp) # Asegurarse de que los cambios en rp se guarden

        request_obj.estado = 'enviado'
        db.session.commit()
        flash('Solicitud de precio marcada como enviada y notificaciones procesadas.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al enviar la solicitud: {e}', 'error')

    return redirect(url_for('price_requests.list_price_requests'))

@price_requests_bp.route('/<int:id>/cotizacion/<int:provider_id>', methods=['GET', 'POST'])
@login_required
def register_provider_quote(id, provider_id):
    if not current_user.has_permission('register_provider_quotes'):
        flash('No tienes permiso para registrar cotizaciones de proveedores.', 'error')
        return redirect(url_for('index'))

    PriceRequest = get_table_class('price_requests')
    PriceRequestProvider = get_table_class('price_request_providers')
    ProviderQuote = get_table_class('provider_quotes')
    Material = get_table_class('materiales')
    Service = get_table_class('servicios')

    request_obj = db.session.query(PriceRequest).filter_by(id=id).first_or_404()
    request_provider_obj = db.session.query(PriceRequestProvider).filter_by(request_id=id, proveedor_id=provider_id).first_or_404()

    if request.method == 'POST':
        # Lógica para registrar la cotización de cada material/servicio
        # Esto podría ser un formulario dinámico o recibir un JSON
        # Por simplicidad, asumimos un solo item por ahora
        material_id = request.form.get('material_id')
        service_id = request.form.get('service_id')
        precio_unitario = request.form.get('precio_unitario', type=float)
        plazo_entrega = request.form.get('plazo_entrega')
        notas = request.form.get('notas')

        try:
            new_quote = ProviderQuote(
                request_provider_id=request_provider_obj.id,
                material_id=material_id if material_id else None,
                service_id=service_id if service_id else None,
                precio_unitario=precio_unitario,
                plazo_entrega=plazo_entrega,
                notas=notas
            )
            db.session.add(new_quote)
            db.session.commit()
            flash('Cotización registrada con éxito.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al registrar cotización: {e}', 'error')

        return redirect(url_for('price_requests.edit_price_request', id=id))

    # Obtener los items de la solicitud para este proveedor
    PriceRequestItem = get_table_class('price_request_items')
    request_items = db.session.query(PriceRequestItem).filter_by(request_id=id).all()

    return render_template('price_requests/quote_form.html',
                           request=request_obj,
                           request_provider=request_provider_obj,
                           request_items=request_items,
                           materials=db.session.query(Material).all(),
                           services=db.session.query(Service).all())

@price_requests_bp.route('/<int:id>/comparar')
@login_required
def compare_quotes(id):
    if not current_user.has_permission('view_price_comparison'):
        flash('No tienes permiso para ver la comparación de cotizaciones.', 'error')
        return redirect(url_for('index'))

    PriceRequest = get_table_class('price_requests')
    PriceRequestItem = get_table_class('price_request_items')
    PriceRequestProvider = get_table_class('price_request_providers')
    ProviderQuote = get_table_class('provider_quotes')
    Material = get_table_class('materiales')
    Service = get_table_class('servicios')
    Provider = get_table_class('providers')

    request_obj = db.session.query(PriceRequest).filter_by(id=id).first_or_404()

    # Obtener todos los items de la solicitud
    request_items = db.session.query(PriceRequestItem).filter_by(request_id=id).all()

    # Obtener todos los proveedores asociados a esta solicitud
    request_providers = db.session.query(PriceRequestProvider).filter_by(request_id=id).all()

    # Diccionario para almacenar los datos de comparación
    comparison_data = {
        'provider_names': [],
        'items': {} # {item_name: {provider_name: quote_obj}}
    }

    # Rellenar nombres de proveedores
    for rp in request_providers:
        provider = db.session.query(Provider).filter_by(id=rp.proveedor_id).first()
        if provider:
            comparison_data['provider_names'].append(provider.nombre)

    # Rellenar datos de items y cotizaciones
    for item in request_items:
        item_name = ""
        if item.material_id:
            material = db.session.query(Material).filter_by(id=item.material_id).first()
            if material:
                item_name = material.nombre
        elif item.service_id:
            service = db.session.query(Service).filter_by(id=item.service_id).first()
            if service:
                item_name = service.nombre

        if item_name:
            comparison_data['items'][item_name] = {}
            for rp in request_providers:
                provider = db.session.query(Provider).filter_by(id=rp.proveedor_id).first()
                if provider:
                    quote = db.session.query(ProviderQuote).filter_by(
                        request_provider_id=rp.id,
                        material_id=item.material_id,
                        service_id=item.service_id
                    ).first()
                    comparison_data['items'][item_name][provider.nombre] = quote

    return render_template('price_requests/comparison.html',
                           request=request_obj,
                           comparison_data=comparison_data)

@price_requests_bp.route('/generar-pedido-desde-cotizacion/<int:request_id>/<int:quote_id>', methods=['POST'])
@login_required
def generate_order_from_quote(request_id, quote_id):
    if not current_user.has_permission('generate_order_from_quote'):
        flash('No tienes permiso para generar pedidos desde cotizaciones.', 'error')
        return redirect(url_for('index'))

    # Lógica para generar el pedido (a implementar)
    flash('Pedido generado con éxito (funcionalidad en desarrollo).', 'success')
    return redirect(url_for('price_requests.list_price_requests'))

# Registrar el blueprint en __init__.py
# from backend import price_requests
# app.register_blueprint(price_requests.price_requests_bp)

@price_requests_bp.route('/<int:id>/seleccionar-proveedores', methods=['GET', 'POST'])
@login_required
def select_providers_for_request(id):
    if not current_user.has_permission('manage_price_requests_providers'):
        flash('No tienes permiso para gestionar proveedores en solicitudes de precio.', 'error')
        return redirect(url_for('index'))

    PriceRequest = get_table_class('price_requests')
    Provider = get_table_class('providers')
    PriceRequestProvider = get_table_class('price_request_providers')

    request_obj = db.session.query(PriceRequest).filter_by(id=id).first_or_404()
    all_providers = db.session.query(Provider).all()
    request_providers = db.session.query(PriceRequestProvider).filter_by(request_id=id).all()

    if request.method == 'POST':
        provider_ids = request.form.getlist('provider_ids')

        try:
            # Eliminar proveedores que ya no están seleccionados
            existing_provider_ids = [rp.proveedor_id for rp in request_providers]
            for existing_id in existing_provider_ids:
                if str(existing_id) not in provider_ids:
                    db.session.query(PriceRequestProvider).filter_by(request_id=id, proveedor_id=existing_id).delete()

            # Añadir nuevos proveedores seleccionados
            for provider_id in provider_ids:
                if int(provider_id) not in existing_provider_ids:
                    new_prp = PriceRequestProvider(
                        request_id=request_obj.id,
                        proveedor_id=int(provider_id),
                        estado_envio='pendiente'
                    )
                    db.session.add(new_prp)
            db.session.commit()
            flash('Proveedores de la solicitud actualizados con éxito.', 'success')
            return redirect(url_for('price_requests.select_providers_for_request', id=id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar proveedores: {e}', 'error')

    return render_template('price_requests/select_providers.html',
                           request=request_obj,
                           all_providers=all_providers,
                           request_providers=request_providers)

# Registrar el blueprint en __init__.py
# from backend import price_requests
# app.register_blueprint(price_requests.price_requests_bp)
