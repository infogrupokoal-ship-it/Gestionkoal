# backend/__init__.py
import json
import logging
import os
import sys
import time
import uuid
from time import perf_counter

import sentry_sdk
from flask import (
    Flask,
    current_app,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    render_template_string,
    request,
    send_from_directory,
    url_for,
)
from flask_login import AnonymousUserMixin, LoginManager, current_user, login_required
from jinja2 import TemplateNotFound
from sentry_sdk.integrations.flask import FlaskIntegration
from werkzeug.routing import BuildError

from .extensions import db as sqla_db, migrate
from . import db as legacy_db
from .metrics import get_dashboard_kpis

# .env (opcional pero recomendable)
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

app_start_time = time.time()

login_manager = LoginManager()
login_manager.login_view = "auth.login"
class JsonFormatter(logging.Formatter):
    def format(self, record):
        try:
            from flask import g, has_request_context, request  # Import locally for safety

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


# --- GEMINI MODEL NORMALIZER (Helper for model name sanitization) ---
def _normalize_gemini_model(raw: str | None) -> str:
    if not raw:
        return "models/gemini-flash-latest"
    alias = raw.strip().lower()
    mapping = {
        "gemini-1.5-flash": "models/gemini-flash-latest",
        "gemini-flash": "models/gemini-flash-latest",
        "flash": "models/gemini-flash-latest",
    }
    return mapping.get(alias, raw.strip())


def create_app():
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder='../templates',
        static_folder='../static',
    )
    os.makedirs(app.instance_path, exist_ok=True)

    # --- API Keys Configuration ---
    # 1. Gemini API Key (for AI Chat)
    # The user's specific test key is used as a fallback.
    app.config['GEMINI_API_KEY'] = os.environ.get("GEMINI_API_KEY") or 'AIzaSyDZuzsA2qEde_oZ-9D_ag06cDyHwu8XGz8'
    app.config['AI_CHAT_ENABLED'] = bool(app.config['GEMINI_API_KEY'])
    if not os.environ.get("GEMINI_API_KEY"):
        app.logger.warning("Gemini API key not set in environment, using hardcoded test key.")
    else:
        app.logger.info("Gemini API key loaded from environment.")

    # 2. Google Custom Search API (for Market Study)
    app.config['GOOGLE_CSE_API_KEY'] = os.environ.get("GOOGLE_CSE_API_KEY")
    app.config['GOOGLE_CSE_ID'] = os.environ.get("GOOGLE_CSE_ID")
    if not app.config['GOOGLE_CSE_API_KEY'] or not app.config['GOOGLE_CSE_ID']:
        app.logger.warning(
            "Google Custom Search API keys (GOOGLE_CSE_API_KEY or GOOGLE_CSE_ID) not set. Market study will use mock data."
        )
    else:
        app.logger.info("Google Custom Search API keys loaded from environment.")

    # 3. WhatsApp Configuration (with test fallbacks)
    app.config['WHATSAPP_ACCESS_TOKEN'] = os.environ.get("WHATSAPP_ACCESS_TOKEN") or 'test_whatsapp_token'
    app.config['WHATSAPP_PHONE_NUMBER_ID'] = os.environ.get("WHATSAPP_PHONE_NUMBER_ID") or 'test_phone_id'
    app.config['WHATSAPP_VERIFY_TOKEN'] = os.environ.get("WHATSAPP_VERIFY_TOKEN") or 'test_verify_token'
    app.config['WHATSAPP_APP_SECRET'] = os.environ.get("WHATSAPP_APP_SECRET") or 'test_app_secret'



    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        DATABASE=os.environ.get(
            'DATABASE_PATH',
            os.path.join(app.instance_path, 'gestion_avisos.sqlite'),
        ),
        UPLOAD_FOLDER=os.environ.get(
            'UPLOAD_FOLDER',
            os.path.join(os.getcwd(), 'uploads'),
        ),
    )

    # --- NEW: SQLAlchemy Configuration ---
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{app.config['DATABASE']}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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
        dsn=os.environ.get("SENTRY_DSN"),  # Use os.environ.get for safety
        integrations=[FlaskIntegration()],
        traces_sample_rate=0.2,  # performance
    )
    # --- END SENTRY SDK INITIALIZATION ---

    # --- NEW LOGGER SETUP (JSON) ---
    if not app.logger.handlers:
        # Initialize Google Cloud Logging client
        try:
            import google.cloud.logging

            client = google.cloud.logging.Client()
            # Attach a Cloud Logging handler to the root logger
            client.setup_logging(log_http=True)
            app.logger.info("Google Cloud Logging initialized.")
        except Exception as e:
            app.logger.warning(f"Could not initialize Google Cloud Logging: {e}")

        # Stream handler for JSON logs to stdout (for Render logs)
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(JsonFormatter())
        app.logger.addHandler(stream_handler)

        # File handler for local error.log (keep this for local file logging)
        log_file = os.path.join(app.instance_path, 'error.log')
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            )
        )
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

    # --- NEW: Initialize DB and Migrate ---
    db.init_app(app)
    migrate.init_app(app, db)

    # --- Autenticación ---
    login_manager.init_app(app)

    import importlib
    import backend.models
    importlib.reload(backend.models)
    from backend.models import User

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

    @app.before_request  # Existing before_request hook
    def load_logged_in_user_to_g():
        g.user = current_user

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
                conn = legacy_db.get_db()
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

    @app.get("/api/ai/ping", endpoint="ai_ping")
    def ai_ping_alias():
        return jsonify({
            "ok": True,
            "ai_chat_enabled": current_app.config.get("AI_CHAT_ENABLED", False)
        }), 200

    @app.post("/api/ai/chat", endpoint="ai_chat")
    def ai_chat_alias():
        data = request.get_json(silent=True) or {}
        message = (data.get("message") or request.form.get("message") or "").strip()
        if not message:
            return jsonify({"error": "message is required"}), 400
        # Alias simple (eco). La UI real está en /ai_chat/.
        return jsonify({"reply": f"Echo: {message}"}), 200

    # --- Health Check ---
    @app.get("/health")  # Changed from /healthz to /health as per instructions
    def health_check():
        return jsonify({"status": "ok"}), 200


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
        db = legacy_db.get_db() # Use legacy_db for consistency
        if db is None:
            app.logger.error("Database connection error in api_trabajos.")
            return jsonify({"error": "Database connection error"}), 500

        query = """
            SELECT
                t.id,
                t.descripcion as title,
                t.created_at as start,
                NULL as end,
                'job' as type
            FROM tickets t
        """

        events = db.execute(query).fetchall()

        # Convert the list of Row objects to a list of dictionaries
        events_list = [dict(row) for row in events]

        return jsonify(events_list)

    @app.get("/api/dashboard/kpis")
    @login_required # Added login_required as per previous context
    def api_dashboard_kpis():
        try:
            conn = legacy_db.get_db()
            data = get_dashboard_kpis(conn)
            return jsonify({"ok": True, "data": data})
        except Exception as e:
            app.logger.exception("Error in /api/dashboard/kpis: %s", e)
            return jsonify({"ok": False, "error": str(e)}), 500




    # Register Blueprints
    from . import (
        about,
        accounting,
        ai_chat,
        asset_management,
        auth,
        autocomplete,
        catalog,
        clients,
        feedback,
        financial_transactions,
        freelancer_quotes,
        freelancers,
        jobs,
        market_study,
        material_research,
        materials,
        notifications,
        payment_confirmation,
        profile,
        providers,
        quotes,
        reports,
        scheduled_maintenance,
        services,
        shared_expenses,
        stock_movements,
        users,
        whatsapp_meta,
        whatsapp_twilio,
    )

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
    app.register_blueprint(whatsapp_meta.whatsapp_meta_bp)
    app.register_blueprint(accounting.bp)  # Register the new accounting blueprint

    # --- NEW: Register custom CLI commands ---
    from .cli import register_cli

    register_cli(app)
    # --- END NEW ---

    return app