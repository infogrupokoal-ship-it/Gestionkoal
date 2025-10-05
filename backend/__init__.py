# backend/__init__.py
import os
from logging.handlers import RotatingFileHandler
import logging
import sys
from datetime import timedelta
from jinja2 import TemplateNotFound
import re

# .env (opcional pero recomendable)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from flask import (
    Flask, render_template, render_template_string, request, redirect, url_for, jsonify,
    g, flash, send_from_directory, current_app, has_request_context
)
from werkzeug.routing import BuildError
from flask_login import current_user

# --- NEW IMPORTS FOR SENTRY AND JSON LOGGING ---
import json
import time
import uuid
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
import hashlib
from time import perf_counter

app_start_time = time.time()
# --- END NEW IMPORTS ---

# --- NEW JSON FORMATTER CLASS ---
class JsonFormatter(logging.Formatter):
    def format(self, record):
        try:
            from flask import has_request_context, request, g # Import locally for safety
            if has_request_context():
                rid = getattr(g, "request_id", None)
                path = getattr(request, "path", None)
                user_id_hashed = getattr(g, "user_id_hashed", None)
            else:
                rid, path, user_id_hashed = None, None, None
        except Exception:
            rid, path, user_id_hashed = None, None, None

        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "service": "GestionKoal",
            "version": os.environ.get("APP_VERSION", "dev"),
            "message": record.getMessage(),
            "logger": record.name,
            "request_id": rid,
            "user_id_hashed": user_id_hashed,
            "path": path,
            "latency_ms": getattr(record, "latency_ms", None),
        }
        return json.dumps(payload, ensure_ascii=False)
# --- END JSON FORMATTER CLASS ---

# --- GEMINI MODEL NORMALIZER (Helper for model name sanitization) ---
def _normalize_gemini_model(raw: str | None) -> str:
    if not raw:
        return "models/gemini-flash-latest"
    alias = raw.strip().lower()
    mapping = {
        "gemini-1.5-flash": "models/gemini-flash-latest",
        "gemini-flash":     "models/gemini-flash-latest",
        "flash":            "models/gemini-flash-latest",
    }
    return mapping.get(alias, raw.strip())
# --- END GEMINI MODEL NORMALIZER ---

def create_app():
    from flask import flash, redirect, has_request_context # Moved here to ensure availability
    app = Flask(__name__, instance_relative_config=True, template_folder='../templates', static_folder='../static')
    os.makedirs(app.instance_path, exist_ok=True)

    # --- AI Chat & Gemini Configuration ---
    TEST_GOOGLE_API_KEY = "AIzaSyDeC36URGpG3SZOok-SRSZ9Pb_uVv1QIk0" # Fallback for local dev
    gemini_api_key = (
        os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
        or TEST_GOOGLE_API_KEY
    )
    app.config['GEMINI_API_KEY'] = gemini_api_key
    app.config['AI_CHAT_ENABLED'] = bool(gemini_api_key)

    # --- Google Custom Search API Configuration ---
    app.config['GOOGLE_API_KEY'] = os.environ.get("GOOGLE_API_KEY") # Custom Search API Key
    app.config['GOOGLE_CSE_ID'] = os.environ.get("GOOGLE_CSE_ID")

    if not app.config['GOOGLE_API_KEY'] or not app.config['GOOGLE_CSE_ID']:
        app.logger.warning("Google Custom Search API keys (GOOGLE_API_KEY or GOOGLE_CSE_ID) not set. Market study web search will use mock data.")
    else:
        app.logger.info("Google Custom Search API keys: tomadas de entorno.")

    # --- WhatsApp Configuration ---
    app.config['WHATSAPP_ACCESS_TOKEN'] = os.environ.get("WHATSAPP_ACCESS_TOKEN")
    app.config['WHATSAPP_PHONE_NUMBER_ID'] = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
    app.config['WHATSAPP_VERIFY_TOKEN'] = os.environ.get("WHATSAPP_VERIFY_TOKEN")
    app.config['WHATSAPP_APP_SECRET'] = os.environ.get("WHATSAPP_APP_SECRET")

    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        app.logger.warning("Gemini API key: usando CLAVE DE PRUEBA incrustada (entorno no establecido)")
    else:
        app.logger.info("Gemini API key: tomada de entorno")

    app.logger.info("AI chat enabled: %s", app.config['AI_CHAT_ENABLED'])

    # --- Gemini Model Configuration ---
    app.config["GEMINI_MODEL"] = _normalize_gemini_model(
        os.environ.get("GEMINI_MODEL", "models/gemini-flash-latest")
    )
    app.logger.info("Gemini model: %s", app.config["GEMINI_MODEL"])

    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        DATABASE=os.environ.get('DATABASE_PATH', os.path.join(app.instance_path, 'gestion_avisos.sqlite')),
        UPLOAD_FOLDER=os.environ.get('UPLOAD_FOLDER', os.path.join(os.getcwd(), 'uploads')),
    )

    # load the instance config, if it exists, when not testing
    app.config.from_pyfile('config.py', silent=True)
    # --- END AI Chat Configuration ---

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # --- SENTRY SDK INITIALIZATION ---
    sentry_sdk.init(
        dsn=os.environ.get("SENTRY_DSN"), # Use os.environ.get for safety
        integrations=[FlaskIntegration()],
        traces_sample_rate=0.2  # performance
    )
    # --- END SENTRY SDK INITIALIZATION ---

    # --- NEW LOGGER SETUP (JSON) ---
    if not app.logger.handlers:
        # Stream handler for JSON logs to stdout (for Render logs)
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(JsonFormatter())
        app.logger.addHandler(stream_handler)

        # File handler for local error.log (keep this for local file logging)
        log_file = os.path.join(app.instance_path, 'error.log')
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.ERROR)  # Log only ERROR and CRITICAL messages to the file
        app.logger.addHandler(file_handler)

    app.logger.propagate = False
    app.logger.setLevel(logging.INFO)  # Set app logger to INFO to capture all levels of logs
    app.logger.info('--- Iniciando aplicación Gestión Koal ---')
    app.logger.info('Modo de depuración: %s', app.debug)
    app.logger.info('Carpeta de instancia: %s', app.instance_path)
    app.logger.info('Carpeta de subidas: %s', app.config['UPLOAD_FOLDER'])
    app.logger.info('Usando base de datos en: %s', app.config['DATABASE'])
    app.logger.info('Sentry DSN configurado: %s', 'Sí' if os.environ.get("SENTRY_DSN") else 'No')
    app.logger.info('--- Aplicación lista para recibir peticiones ---')
    # --- END NEW LOGGER SETUP ---

    from .metrics import get_dashboard_kpis
    from . import db as dbmod
    
    # --- Autenticación ---
    from flask_login import LoginManager, login_required, AnonymousUserMixin
    from backend.auth import User

    login_manager = LoginManager()
    login_manager.login_view = "auth.login" # Corrected to use blueprint name
    login_manager.init_app(app)

    class Anonymous(AnonymousUserMixin):
        def has_permission(self, *_args, **_kwargs):
            return False

    login_manager.anonymous_user = Anonymous

    @app.context_processor
    def template_helpers():
        def safe_url_for(endpoint, **values):
            try:
                return url_for(endpoint, **values)
            except BuildError:
                return None
        return {
            "safe_url_for": safe_url_for,
            "AI_CHAT_ENABLED": current_app.config.get("AI_CHAT_ENABLED", False),
        }










    # --- NEW before_request HOOK for request_id ---
    @app.before_request
    def inject_request_id():
        g.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        g._t0 = perf_counter()
    # --- END NEW before_request HOOK ---

    @app.before_request # Existing before_request hook
    def load_logged_in_user_to_g():
        g.user = current_user

    @login_manager.user_loader
    def load_user(user_id):
        conn = dbmod.get_db()
        user_row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if user_row:
            return User.from_row(user_row)
        return None

    # --- Simplified Global Error Handler ---
    @app.errorhandler(Exception)
    def handle_exception(e):
        # Log the full exception and traceback to the error.log file
        app.logger.error('An unhandled exception occurred: %s', str(e), exc_info=True)
        # Return a generic error page to the user
        return "Se ha producido un error interno en el servidor. El administrador ha sido notificado.", 500

    # --- Ruta raíz (Dashboard o Login) ---
    @app.route("/")
    def index():
        if current_user.is_authenticated:
            try:
                conn = dbmod.get_db()
                if conn is None:
                    flash('Database connection error.', 'error')
                    return redirect(url_for("auth.login"))
                
                kpis = get_dashboard_kpis(conn)
                
                # The original query for recent tickets can be kept if needed
                tickets = conn.execute(
                    "SELECT t.id, t.descripcion as title, t.estado, t.created_at, c.nombre as client_nombre, u.username as assigned_user_username "
                    "FROM tickets t LEFT JOIN clientes c ON t.cliente_id = c.id LEFT JOIN users u ON t.asignado_a = u.id "
                    "ORDER BY t.created_at DESC LIMIT 10"
                ).fetchall()

                return render_template(
                    "dashboard.html",
                    kpis=kpis,
                    tickets=tickets
                )
            except TemplateNotFound:
                app.logger.warning("dashboard.html no encontrado; sirviendo vista mínima de fallback.")
                # Fallback HTML mínimo para que la raíz no rompa aunque falte la plantilla
                return render_template_string(
                    """
                    <!doctype html>
                    <meta charset="utf-8">
                    <title>Gestión Koal — Dashboard (placeholder)</title>
                    <h1>Dashboard (placeholder)</h1>
                    <p>No se encontró <code>dashboard.html</code>. Crea <code>backend/templates/dashboard.html</code>
                    o ajusta <code>template_folder</code> en <code>Flask(...)</code>.</p>
                    <h2>KPIs</h2>
                    <pre>{{ kpis|tojson(indent=2) }}</pre>
                    <h2>Tickets</h2>
                    <pre>{{ tickets|tojson(indent=2) }}</pre>
                    """,
                    kpis=kpis, tickets=tickets
                ), 200
            except Exception as e:
                app.logger.exception("An unhandled exception occurred: %s", e)
                return jsonify({"error": "internal server error"}), 500
        else:
            return redirect(url_for("auth.login"))

    @app.get("/ai/ping", endpoint="ai_ping")
    def ai_ping_alias():
        return jsonify({
            "ok": True,
            "ai_chat_enabled": current_app.config.get("AI_CHAT_ENABLED", False)
        }), 200

    @app.post("/ai/chat", endpoint="ai_chat")
    def ai_chat_alias():
        data = request.get_json(silent=True) or {}
        message = (data.get("message") or request.form.get("message") or "").strip()
        if not message:
            return jsonify({"error": "message is required"}), 400
        # Alias simple (eco). La UI real está en /ai_chat/.
        return jsonify({"reply": f"Echo: {message}"}), 200

    # --- Health Check ---
    @app.get("/healthz")
    def health_check():
        return jsonify({"status": "ok"}), 200

    from flask import send_from_directory

    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    @app.route('/favicon.ico')
    def favicon():
        static_dir = os.path.join(app.root_path, 'static')
        favicon_path = os.path.join(static_dir, 'favicon.ico')
        if os.path.exists(favicon_path):
            return send_from_directory(
                static_dir,
                'favicon.ico',
                mimetype='image/vnd.microsoft.icon'
            )
        # Si no existe, no lo tratamos como error
        return ("", 204)

    @app.route('/api/trabajos')
    @login_required
    def api_trabajos():
        """
        API endpoint to fetch jobs/events for the FullCalendar.
        """
        db = dbmod.get_db() # Use dbmod for consistency

        query = """
            SELECT
                t.id,
                t.descripcion as title,
                COALESCE(e.inicio, t.created_at) as start,
                e.fin as end,
                'job' as type
            FROM tickets t
            LEFT JOIN eventos e ON t.id = e.ticket_id
            UNION ALL
            SELECT
                mp.id,
                COALESCE(mp.descripcion, mp.tipo_mantenimiento) as title,
                mp.proxima_fecha_mantenimiento as start,
                NULL as end,
                'maintenance' as type
            FROM mantenimientos_programados mp
            WHERE mp.estado = 'activo'
        """
        
        events = db.execute(query).fetchall()
        
        # Convert the list of Row objects to a list of dictionaries
        events_list = [dict(row) for row in events]
        
        return jsonify(events_list)

    @app.get("/api/dashboard/kpis")
    def api_dashboard_kpis():
        try:
            conn = dbmod.get_db()
            data = get_dashboard_kpis(conn)
            return jsonify({"ok": True, "data": data})
        except Exception as e:
            app.logger.exception("Error in /api/dashboard/kpis: %s", e)
            return jsonify({"ok": False, "error": str(e)}), 500

    dbmod.init_app(app)
    dbmod.register_commands(app)

    # Register Blueprints
    from . import auth, jobs, clients, services, materials, providers, freelancers, users, about, reports, notifications, profile, quotes, scheduled_maintenance, feedback, ai_chat, stock_movements, material_research, market_study, financial_transactions, shared_expenses, payment_confirmation, freelancer_quotes, asset_management, whatsapp_twilio, catalog, autocomplete, whatsapp_meta
    app.register_blueprint(auth.bp)
    app.register_blueprint(jobs.bp)
    app.register_blueprint(clients.bp)
    app.register_blueprint(services.bp)
    app.register_blueprint(materials.bp)
    app.register_blueprint(providers.bp)
    app.register_blueprint(freelancers.bp)
    app.register_blueprint(users.bp)
    app.register_blueprint(about.bp)
    app.register_blueprint(reports.bp)
    app.register_blueprint(notifications.bp)
    app.register_blueprint(profile.bp)
    app.register_blueprint(quotes.bp)
    app.register_blueprint(scheduled_maintenance.bp)
    app.register_blueprint(feedback.bp)
    try:
        from . import ai_chat
        app.register_blueprint(ai_chat.bp)
    except Exception as e:
        app.logger.warning("AI chat deshabilitado: %s", e)
    app.register_blueprint(stock_movements.bp)
    app.register_blueprint(material_research.bp)
    app.register_blueprint(market_study.bp)
    app.register_blueprint(financial_transactions.bp)
    app.register_blueprint(shared_expenses.bp)
    app.register_blueprint(payment_confirmation.bp)
    app.register_blueprint(freelancer_quotes.bp)
    app.register_blueprint(asset_management.bp)
    app.register_blueprint(whatsapp_twilio.bp)
    app.register_blueprint(catalog.bp)
    app.register_blueprint(autocomplete.bp)
    app.register_blueprint(whatsapp_meta.bp)
    from . import accounting # Import the new accounting blueprint
    app.register_blueprint(accounting.bp) # Register the new accounting blueprint

    return app
