import os
import secrets
from datetime import datetime, timedelta

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
from sqlalchemy import text

from backend.activity_log import add_activity_log
from backend.extensions import db
from backend.models import get_table_class
from backend.pdf_utils import generate_quote_pdf
from backend.whatsapp import WhatsAppClient

bp = Blueprint("quotes", __name__, url_prefix="/quotes")


@bp.route("/")
@login_required
def list_quotes():
    if not current_user.has_permission("manage_quotes"):
        flash("No tienes permiso para gestionar presupuestos.", "error")
        return redirect(url_for("index"))
    try:
        query_text = """
            SELECT p.id, p.ticket_id, p.estado, p.total, p.fecha_creacion, 
                   t.titulo as job_title, 
                   c.nombre as client_name,
                   u.username as comercial_name
            FROM presupuestos p
            LEFT JOIN tickets t ON p.ticket_id = t.id
            LEFT JOIN clientes c ON t.cliente_id = c.id
            LEFT JOIN users u ON p.comercial_id = u.id
        """
        params = {}

        if current_user.has_role('comercial'):
            query_text += " WHERE p.comercial_id = :user_id"
            params["user_id"] = current_user.id
        
        query_text += " ORDER BY p.fecha_creacion DESC"
        
        quotes = db.session.execute(text(query_text), params).fetchall()
        return render_template("quotes/list.html", quotes=quotes)
    except Exception as e:
        current_app.logger.error(f"Error in list_quotes: {e}", exc_info=True)
        flash("Ocurrió un error al cargar los presupuestos.", "error")
        return redirect(url_for("index"))


@bp.route("/trabajos/<int:trabajo_id>/add", methods=("GET", "POST"))
@login_required
def add_quote(trabajo_id):
    if not current_user.has_permission("create_quotes"):
        flash("No tienes permiso para crear presupuestos.", "error")
        return redirect(url_for("jobs.list_jobs"))
    try:
        trabajo = db.session.execute(
            text("SELECT * FROM tickets WHERE id = :trabajo_id"),
            {"trabajo_id": trabajo_id},
        ).fetchone()

        if trabajo is None:
            flash("El trabajo no existe.")
            return redirect(url_for("jobs.list_jobs"))

        if request.method == "POST":
            estado = request.form.get("estado", "borrador")
            fecha_vencimiento = request.form.get("fecha_vencimiento")
            total = 0.0
            items_data = []
            error = None

            descripciones = request.form.getlist("item_descripcion[]")
            quantities = request.form.getlist("item_qty[]")
            unit_prices = request.form.getlist("item_precio_unit[]")

            for i in range(len(descripciones)):
                descripcion = descripciones[i].strip()
                qty_str = quantities[i].strip()
                precio_unit_str = unit_prices[i].strip()

                if not descripcion and (not qty_str or not precio_unit_str):
                    continue

                try:
                    qty = float(qty_str) if qty_str else 0.0
                    precio_unit = float(precio_unit_str) if precio_unit_str else 0.0
                except ValueError:
                    error = "Cantidad y Precio Unitario deben ser números válidos."
                    break

                if not descripcion:
                    error = "La descripción del ítem no puede estar vacía si hay cantidad o precio."
                    break

                item_total = qty * precio_unit
                total += item_total
                items_data.append(
                    {"descripcion": descripcion, "qty": qty, "precio_unit": precio_unit}
                )

            if error is not None:
                flash(error)
            elif not items_data:
                flash("Debe añadir al menos un ítem al presupuesto.")
            else:
                try:
                    result = db.session.execute(
                        text(
                            "INSERT INTO presupuestos (ticket_id, comercial_id, estado, total, fecha_vencimiento) VALUES (:ticket_id, :comercial_id, :estado, :total, :fecha_vencimiento)"
                        ),
                        {"ticket_id": trabajo_id, "comercial_id": trabajo.comercial_id, "estado": estado, "total": total, "fecha_vencimiento": fecha_vencimiento},
                    )
                    presupuesto_id = result.lastrowid

                    for item in items_data:
                        db.session.execute(
                            text(
                                "INSERT INTO presupuesto_items (presupuesto_id, descripcion, qty, precio_unit) VALUES (:presupuesto_id, :descripcion, :qty, :precio_unit)"
                            ),
                            {
                                "presupuesto_id": presupuesto_id,
                                "descripcion": item["descripcion"],
                                "qty": item["qty"],
                                "precio_unit": item["precio_unit"],
                            },
                        )

                    add_activity_log('create_quote', 'quote', presupuesto_id, f'Presupuesto creado para el trabajo #{trabajo_id}')
                    db.session.commit()
                    flash("¡Presupuesto creado correctamente!")
                    return redirect(url_for("jobs.edit_job", job_id=trabajo_id))

                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error in add_quote: {e}", exc_info=True)
                    error = f"Ocurrió un error al guardar el presupuesto: {e}"
                    flash(error)

        return render_template("quotes/form.html", trabajo=trabajo, presupuesto=None, estados=['borrador', 'enviado', 'aceptado', 'rechazado', 'vencido'])
    except Exception as e:
        current_app.logger.error(f"Error in add_quote: {e}", exc_info=True)
        flash("Ocurrió un error al cargar el formulario de presupuesto.", "error")
        return redirect(url_for("jobs.list_jobs"))


@bp.route("/<int:quote_id>/view", methods=("GET", "POST"))
@login_required
def view_quote(quote_id):
    if not current_user.has_permission("manage_quotes"):
        flash("No tienes permiso para ver este presupuesto.", "error")
        return redirect(url_for("index"))
    try:
        from sqlalchemy.orm import aliased
        User = get_table_class("users")
        Partner = aliased(User)
        
        query = text("""
            SELECT p.*, t.comercial_id, partner.username as comercial_name
            FROM presupuestos p
            JOIN tickets t ON p.ticket_id = t.id
            LEFT JOIN users partner ON t.comercial_id = partner.id
            WHERE p.id = :quote_id
        """)
        if presupuesto is None:
            flash("Presupuesto no encontrado.")
            return redirect(url_for("jobs.list_jobs"))

        # Permission check for 'comercial' role
        if current_user.has_role('comercial') and presupuesto.comercial_id != current_user.id:
            flash("No tienes permiso para ver este presupuesto.", "error")
            return redirect(url_for("jobs.list_jobs"))

        items = db.session.execute(
            text(
                "SELECT id, descripcion, qty, precio_unit FROM presupuesto_items WHERE presupuesto_id = :quote_id"
            ),
            {"quote_id": quote_id},
        ).fetchall()

        if request.method == "POST":
            estado = request.form.get("estado", "borrador")
            fecha_vencimiento = request.form.get("fecha_vencimiento")
            total = 0.0
            items_to_process = []
            error = None

            item_ids = request.form.getlist("item_id[]")
            descripciones = request.form.getlist("item_descripcion[]")
            quantities = request.form.getlist("item_qty[]")
            unit_prices = request.form.getlist("item_precio_unit[]")

            for i in range(len(descripciones)):
                item_id_str = item_ids[i].strip()
                descripcion = descripciones[i].strip()
                qty_str = quantities[i].strip()
                precio_unit_str = unit_prices[i].strip()

                if (
                    not descripcion
                    and not item_id_str
                    and (not qty_str or not precio_unit_str)
                ):
                    continue

                try:
                    qty = float(qty_str) if qty_str else 0.0
                    precio_unit = float(precio_unit_str) if precio_unit_str else 0.0
                except ValueError:
                    error = "Cantidad y Precio Unitario deben ser números válidos."
                    break

                if not descripcion:
                    error = "La descripción del ítem no puede estar vacía si hay cantidad o precio."
                    break

                item_total = qty * precio_unit
                total += item_total
                items_to_process.append(
                    {
                        "id": int(item_id_str) if item_id_str else None,
                        "descripcion": descripcion,
                        "qty": qty,
                        "precio_unit": precio_unit,
                    }
                )

            if error is not None:
                flash(error)
            elif not items_to_process:
                flash("Debe añadir al menos un ítem al presupuesto.")
            else:
                try:
                    db.session.execute(
                        text(
                            "UPDATE presupuestos SET estado = :estado, total = :total, fecha_vencimiento = :fecha_vencimiento, comercial_id = :comercial_id WHERE id = :quote_id"
                        ),
                        {"estado": estado, "total": total, "fecha_vencimiento": fecha_vencimiento, "comercial_id": presupuesto.comercial_id, "quote_id": quote_id},
                    )

                    existing_item_ids = [
                        item[0] for item in items if item[0] is not None
                    ]
                    submitted_item_ids = [
                        item["id"]
                        for item in items_to_process
                        if item["id"] is not None
                    ]

                    for existing_id in existing_item_ids:
                        if existing_id not in submitted_item_ids:
                            db.session.execute(
                                text(
                                    "DELETE FROM presupuesto_items WHERE id = :existing_id"
                                ),
                                {"existing_id": existing_id},
                            )

                    for item in items_to_process:
                        if item["id"]:
                            db.session.execute(
                                text(
                                    "UPDATE presupuesto_items SET descripcion = :descripcion, qty = :qty, precio_unit = :precio_unit WHERE id = :id"
                                ),
                                {
                                    "descripcion": item["descripcion"],
                                    "qty": item["qty"],
                                    "precio_unit": item["precio_unit"],
                                    "id": item["id"],
                                },
                            )
                        else:
                            db.session.execute(
                                text(
                                    "INSERT INTO presupuesto_items (presupuesto_id, descripcion, qty, precio_unit) VALUES (:presupuesto_id, :descripcion, :qty, :precio_unit)"
                                ),
                                {
                                    "presupuesto_id": quote_id,
                                    "descripcion": item["descripcion"],
                                    "qty": item["qty"],
                                    "precio_unit": item["precio_unit"],
                                },
                            )

                    add_activity_log('update_quote', 'quote', quote_id, f'Presupuesto actualizado. Nuevo estado: {estado}')
                    db.session.commit()
                    flash("¡Presupuesto actualizado correctamente!")
                    return redirect(url_for("quotes.view_quote", quote_id=quote_id))

                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error in view_quote: {e}", exc_info=True)
                    error = f"Ocurrió un error al actualizar el presupuesto: {e}"
                    flash(error)

        return render_template("quotes/view.html", presupuesto=presupuesto, items=items, estados=['borrador', 'enviado', 'aceptado', 'rechazado', 'vencido'])
    except Exception as e:
        current_app.logger.error(f"Error in view_quote: {e}", exc_info=True)
        flash("Ocurrió un error al cargar el presupuesto.", "error")
        return redirect(url_for("jobs.list_jobs"))


@bp.route("/<int:quote_id>/delete", methods=("POST",))
@login_required
def delete_quote(quote_id):
    if not current_user.has_permission("manage_quotes"):
        flash("No tienes permiso para eliminar presupuestos.", "error")
        return redirect(url_for("jobs.list_jobs"))
    try:
        presupuesto = db.session.execute(
            text("SELECT id FROM presupuestos WHERE id = :quote_id"),
            {"quote_id": quote_id},
        ).fetchone()

        if presupuesto is None:
            flash("Presupuesto no encontrado.")
            return redirect(url_for("jobs.list_jobs"))

        db.session.execute(
            text("DELETE FROM presupuesto_items WHERE presupuesto_id = :quote_id"),
            {"quote_id": quote_id},
        )
        db.session.execute(
            text("DELETE FROM presupuestos WHERE id = :quote_id"),
            {"quote_id": quote_id},
        )
        db.session.commit()
        flash("¡Presupuesto eliminado correctamente!")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in delete_quote: {e}", exc_info=True)
        flash(f"Ocurrió un error al eliminar el presupuesto: {e}")

    return redirect(url_for("jobs.list_jobs"))


@bp.route("/<int:quote_id>/duplicate", methods=("POST",))
@login_required
def duplicate_quote(quote_id):
    if not current_user.has_permission("create_quotes"):
        flash("No tienes permiso para duplicar presupuestos.", "error")
        return redirect(request.referrer or url_for("index"))

    try:
        # Fetch original quote
        original_quote = db.session.execute(
            text("SELECT * FROM presupuestos WHERE id = :quote_id"),
            {"quote_id": quote_id},
        ).fetchone()

        if original_quote is None:
            flash("Presupuesto original no encontrado.", "error")
            return redirect(url_for('quotes.list_quotes'))

        # Fetch original items
        original_items = db.session.execute(
            text("SELECT * FROM presupuesto_items WHERE presupuesto_id = :quote_id"),
            {"quote_id": quote_id},
        ).fetchall()

        # Create new quote
        new_quote_result = db.session.execute(
            text("INSERT INTO presupuestos (ticket_id, estado, total) VALUES (:ticket_id, 'borrador', :total)"),
            {"ticket_id": original_quote.ticket_id, "total": original_quote.total}
        )
        new_quote_id = new_quote_result.lastrowid

        # Create new items for the new quote
        for item in original_items:
            db.session.execute(
                text("INSERT INTO presupuesto_items (presupuesto_id, descripcion, qty, precio_unit) VALUES (:presupuesto_id, :descripcion, :qty, :precio_unit)"),
                {"presupuesto_id": new_quote_id, "descripcion": item.descripcion, "qty": item.qty, "precio_unit": item.precio_unit}
            )

        db.session.commit()
        flash("Presupuesto duplicado correctamente. Ahora puedes editar la nueva copia.", "success")
        return redirect(url_for('quotes.view_quote', quote_id=new_quote_id))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error duplicating quote: {e}", exc_info=True)
        flash("Ocurrió un error al duplicar el presupuesto.", "error")
        return redirect(url_for('quotes.list_quotes'))


@bp.route("/send_for_signature/<int:quote_id>", methods=("POST",))
@login_required
def send_quote_for_signature(quote_id):
    if not current_user.has_permission("manage_quotes"):
        flash("No tienes permiso para realizar esta acción.", "error")
        return redirect(request.referrer or url_for("index"))
    try:
        quote = db.session.execute(
            text(
                """SELECT p.id, p.ticket_id, p.total, t.cliente_id, cl.whatsapp_number, cl.nombre as client_name
             FROM presupuestos p
             JOIN tickets t ON p.ticket_id = t.id
             JOIN clientes cl ON t.cliente_id = cl.id
             WHERE p.id = :quote_id"""
            ),
            {"quote_id": quote_id},
        ).fetchone()

        if quote is None:
            flash("Presupuesto no encontrado.", "error")
            return redirect(request.referrer or url_for("index"))

        if not quote[4]:
            flash("El cliente no tiene un número de WhatsApp registrado.", "error")
            return redirect(request.referrer or url_for("index"))

        signature_token = secrets.token_urlsafe(32)
        token_expires = (datetime.now() + timedelta(hours=24)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        db.session.execute(
            text(
                "UPDATE presupuestos SET signature_token = :signature_token, token_expires = :token_expires WHERE id = :quote_id"
            ),
            {
                "signature_token": signature_token,
                "token_expires": token_expires,
                "quote_id": quote_id,
            },
        )
        db.session.commit()

        signature_url = url_for(
            "quotes.client_sign_quote", token=signature_token, _external=True
        )

        client = WhatsAppClient()
        message = f"¡Hola {quote[5]}! Tienes un presupuesto pendiente de firma para el trabajo {quote[1]}. Por favor, fírmalo aquí: {signature_url}"
        client.send_text(quote[4], message)

        flash("Enlace de firma enviado al cliente por WhatsApp.", "success")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Error in send_quote_for_signature: {e}", exc_info=True
        )
        flash(f"Error al enviar el enlace de firma: {e}", "error")

    return redirect(request.referrer or url_for("index"))


@bp.route("/sign/<string:token>", methods=("GET", "POST"))
def client_sign_quote(token):
    try:
        quote = db.session.execute(
            text(
                "SELECT p.*, c.nombre as client_name, cl.whatsapp_number FROM presupuestos p JOIN tickets t ON p.ticket_id = t.id JOIN clientes cl ON t.cliente_id = cl.id WHERE p.signature_token = :token"
            ),
            {"token": token},
        ).fetchone()

        if quote is None:
            flash("Enlace de firma no válido o caducado.", "error")
            return redirect(url_for("auth.login"))

        if quote[8]:
            flash("Este presupuesto ya ha sido firmado.", "info")
            return render_template(
                "quotes/client_sign_quote.html", quote=quote, signed=True
            )

        items = db.session.execute(
            text(
                "SELECT descripcion, qty, precio_unit FROM presupuesto_items WHERE presupuesto_id = :quote_id"
            ),
            {"quote_id": quote[0]},
        ).fetchall()

        if request.method == "POST":
            client_name = request.form.get("client_name")
            signature_data = request.form.get("signature_data")

            if not client_name or not signature_data:
                flash("Por favor, introduce tu nombre y firma el documento.", "error")
                return render_template(
                    "quotes/client_sign_quote.html",
                    quote=quote,
                    items=items,
                    token=token,
                )

            try:
                db.session.execute(
                    text(
                        "UPDATE presupuestos SET client_signature_data = :signature_data, client_signature_date = :signature_date, client_signed_by = :client_name, estado = :estado WHERE id = :quote_id"
                    ),
                    {
                        "signature_data": signature_data,
                        "signature_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "client_name": client_name,
                        "estado": "aceptado",
                        "quote_id": quote[0],
                    },
                )

                # --- Convert to Job Logic ---
                db.session.execute(
                    text("UPDATE tickets SET presupuesto_aprobado = 1 WHERE id = :ticket_id"),
                    {"ticket_id": quote.ticket_id}
                )
                # --- End Convert to Job Logic ---

                add_activity_log('accept_quote', 'quote', quote[0], f'Presupuesto aceptado y firmado por {client_name}')

                pdf_filename = f"presupuesto_firmado_{quote[0]}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
                upload_folder = current_app.config["UPLOAD_FOLDER"]
                os.makedirs(upload_folder, exist_ok=True)
                pdf_filepath = os.path.join(upload_folder, pdf_filename)

                # Fetch client data for PDF
                Client = get_table_class("clientes")
                client_data = db.session.query(Client).filter_by(id=quote.cliente_id).first()

                company_data = {
                    'name': 'Climatizacion Vertical s.l.u',
                    'address': 'Avenida Malvarrosa 112 bajo, Valencia 46011',
                    'cif': 'B40642555'
                }

                generate_quote_pdf(pdf_filepath, dict(quote), items, dict(client_data), company_data)

                signed_pdf_url = url_for(
                    "uploaded_file", filename=pdf_filename, _external=True
                )
                db.session.execute(
                    text(
                        "UPDATE presupuestos SET signed_pdf_url = :signed_pdf_url WHERE id = :quote_id"
                    ),
                    {"signed_pdf_url": signed_pdf_url, "quote_id": quote[0]},
                )
                db.session.commit()

                if quote[6]:
                    client = WhatsAppClient()
                    whatsapp_message = f"¡Hola {quote[5]}! Tu presupuesto {quote[0]} ha sido firmado y aprobado. Puedes verlo aquí: {signed_pdf_url}"
                    client.send_text(quote[6], whatsapp_message)
                    flash("Presupuesto firmado y enviado por WhatsApp.", "success")
                else:
                    flash(
                        "Presupuesto firmado. No se pudo enviar por WhatsApp (número no disponible).",
                        "warning",
                    )

                flash("Presupuesto firmado y aprobado correctamente.", "success")
                return redirect(
                    url_for("quotes.client_sign_quote", token=token, signed=True)
                )

            except Exception as e:
                db.session.rollback()
                current_app.logger.error(
                    f"Error in client_sign_quote: {e}", exc_info=True
                )
                flash(f"Ocurrió un error al procesar la firma: {e}", "error")

        return render_template(
            "quotes/client_sign_quote.html", quote=quote, items=items, token=token
        )
    except Exception as e:
        current_app.logger.error(f"Error in client_sign_quote: {e}", exc_info=True)
        flash("Ocurrió un error al cargar la página de firma.", "error")
        return redirect(url_for("auth.login"))
