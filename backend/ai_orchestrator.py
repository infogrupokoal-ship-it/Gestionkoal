# backend/ai_orchestrator.py
from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy import text
from backend.db_utils import get_db
from backend.whatsapp import WhatsAppClient
from backend.rules_engine import evaluate_policies
from backend.similarity import is_duplicate_of_recent
from backend.assignment import suggest_assignee
from backend.llm import ask_gemini_json
from backend.normalizers import normalize_phone, normalize_priority
from backend.kpis import estimate_sla_due
from backend.extensions import db # Import the global db instance
import os # Added for WHATSAPP_PROVIDER
import json # Added for json.dumps

def process_incoming_text(source: str, raw_phone: str, message_text: str = None, **kwargs):
    # Backward-compat: accept text= as alias for message_text
    if message_text is None:
        message_text = kwargs.get("text")
    current_app.logger.debug(f"process_incoming_text started for phone: {raw_phone}, text: {message_text}")
    phone = normalize_phone(raw_phone)
    
    try:
        # 1) Identificar (o crear) cliente
        client = db.session.execute(text("SELECT * FROM clientes WHERE telefono = :phone"), {"phone": phone}).fetchone()
        if client is None:
            current_app.logger.debug(f"Client not found for phone {phone}. Attempting to create new client.")
            enrich = ask_gemini_json("extract_client_fields", {"message": message_text})
            nombre = enrich.get("nombre") or f"Cliente {phone}"
            email  = enrich.get("email")
            nif    = enrich.get("nif")
            client_result = db.session.execute(text("INSERT INTO clientes (nombre, telefono, email, nif) VALUES (:nombre, :telefono, :email, :nif)"),
                       {"nombre": nombre, "telefono": phone, "email": email, "nif": nif})
            client_id = client_result.lastrowid
            client = db.session.execute(text("SELECT * FROM clientes WHERE id = :client_id"), {"client_id": client_id}).fetchone()
            current_app.logger.debug(f"New client created with ID: {client.id}")
        else:
            current_app.logger.debug(f"Client found with ID: {client.id}")

        # 2) Triage (tipo, prioridad, resumen)
        current_app.logger.debug("Performing triage...")
        triage = ask_gemini_json("triage_ticket", {"message": message_text})
        tipo   = triage.get("tipo")
        prio   = normalize_priority(triage.get("prioridad") or "media")
        titulo = triage.get("titulo") or message_text[:80]
        desc   = triage.get("descripcion") or message_text
        current_app.logger.debug(f"Triage complete. Tipo: {tipo}, Prioridad: {prio}, Titulo: {titulo}")

        # 3) Deduplicación
        current_app.logger.debug("Checking for deduplication...")
        dup_ticket_id = is_duplicate_of_recent(db.session, client.id, titulo, desc, within_minutes=180)
        if dup_ticket_id:
            current_app.logger.debug(f"Duplicate ticket found: {dup_ticket_id}. Logging and returning.")
            db.session.execute(text("INSERT INTO ai_logs (event_type,input,output,ticket_id,client_id,score) VALUES (:event_type, :input, :output, :ticket_id, :client_id, :score)"),
                       {"event_type": "dedup", "input": message_text, "output": f"duplicate_of:{dup_ticket_id}", "ticket_id": dup_ticket_id, "client_id": client.id, "score": 1.0})
            db.session.commit() # Commit this log separately as the function returns here
            return {"ok": True, "duplicated_into": dup_ticket_id}

        # 4) Crear ticket preliminar
        current_app.logger.debug("Creating preliminary ticket...")
        sla_due = estimate_sla_due(priority=prio)
        ticket_result = db.session.execute(
            text("INSERT INTO tickets (cliente_id, source, tipo, prioridad, estado, titulo, descripcion, sla_due, creado_por) VALUES (:cliente_id, :source, :tipo, :prioridad, :estado, :titulo, :descripcion, :sla_due, :creado_por)"),
            {"cliente_id": client.id, "source": source, "tipo": tipo, "prioridad": prio, "estado": "nuevo", "titulo": titulo, "descripcion": desc, "sla_due": sla_due, "creado_por": 1}
        )
        ticket_id = ticket_result.lastrowid
        current_app.logger.debug(f"Preliminary ticket created with ID: {ticket_id}")

        # Add notification for the client
        current_app.logger.debug("Adding notification for the client...")
        notification_message = f"Se ha creado un nuevo ticket para ti: #{ticket_id} - {titulo}"

        # Escoge un user_id válido de la tabla 'users'
        notify_user_id = assignee["id"] if 'assignee' in locals() and assignee and assignee.get("id") else 1

        db.session.execute(
            text("INSERT INTO notifications (user_id, message) VALUES (:user_id, :message)"),
            {"user_id": notify_user_id, "message": notification_message}
        )
        current_app.logger.debug("Notification added.")

        # 5) Políticas/Reglas + Asignación
        current_app.logger.debug("Evaluating policies and suggesting assignee...")
        policy_decision = evaluate_policies(db.session, client, {"tipo": tipo, "prioridad": prio})
        assignee = suggest_assignee(db.session, tipo, prio, client)
        if policy_decision.get("auto_assign") and assignee:
            current_app.logger.debug(f"Auto-assigning ticket {ticket_id} to {assignee['username']}")
            db.session.execute(text("UPDATE tickets SET asignado_a = :asignado_a, estado = :estado WHERE id = :id"),
                       {"asignado_a": assignee["id"], "estado": "asignado", "id": ticket_id})
        current_app.logger.debug("Policies evaluated and assignment suggested.")

        db.session.execute(text("INSERT INTO ai_logs (event_type,input,output,ticket_id,client_id) VALUES (:event_type, :input, :output, :ticket_id, :client_id)"),
                   {"event_type": "triage", "input": message_text, "output": str(triage), "ticket_id": ticket_id, "client_id": client.id})
        current_app.logger.debug("AI log for triage created.")

        # 6) Respuesta al cliente (DRY-RUN respeta config)
        current_app.logger.debug("Preparing WhatsApp response...")
        msg = policy_decision.get("reply_template", "Hemos recibido tu aviso. Te contactamos pronto.")
        wa_response = WhatsAppClient().send_text(phone, msg)
        current_app.logger.debug(f"WhatsApp response sent. Status: {wa_response.get('status', 'unknown')}")
        
        # Log WhatsApp interaction
        current_app.logger.debug("Logging WhatsApp interaction...")
        db.session.execute(
            text("INSERT INTO whatsapp_logs (direction, phone, message, provider, status, error, payload) VALUES (:direction, :phone, :message, :provider, :status, :error, :payload)"),
            {
                "direction": "outbound",
                "phone": phone,
                "message": msg,
                "provider": os.environ.get("WHATSAPP_PROVIDER", "meta"),
                "status": wa_response.get("status", "unknown"),
                "error": wa_response.get("error"),
                "payload": json.dumps(wa_response) # Store full response as JSON
            }
        )
        current_app.logger.debug("WhatsApp interaction logged.")

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in process_incoming_text: {e}", exc_info=True)
        raise
    else:
        current_app.logger.debug("Committing database changes...")
        db.session.commit() # Single commit at the end of a successful transaction
        current_app.logger.debug("Database changes committed. Function returning.")
        return {"ok": True, "ticket_id": ticket_id, "assigned_to": assignee["username"] if assignee else None}
