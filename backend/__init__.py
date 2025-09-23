# backend/__init__.py
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, jsonify, request, redirect, url_for, render_template, g, has_request_context
from flask_login import current_user

# --- NEW IMPORTS FOR SENTRY AND JSON LOGGING ---
import json
import time
import uuid
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
# --- END NEW IMPORTS ---

# --- NEW JSON FORMATTER CLASS ---
class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "request_id": getattr(g, "request_id", None) if has_request_context() and hasattr(g, "request_id") else None,
            "path": request.path if has_request_context() else None,
        }
        if record.exc_info:
            payload["stack"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)
# --- END JSON FORMATTER CLASS ---


def create_app():
    app = Flask(__name__, instance_relative_config=True,
                template_folder='../templates',
                static_folder=os.path.join(os.path.dirname(__file__), "..", "static"))

    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        DATABASE=os.environ.get('DATABASE_PATH', os.path.join(app.instance_path, 'gestion_avisos.sqlite')),
        UPLOAD_FOLDER=os.environ.get('UPLOAD_FOLDER', os.path.join(os.getcwd(), 'uploads')),
    )

    # load the instance config, if it exists, when not testing
    app.config.from_pyfile('config.py', silent=True)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # --- SENTRY SDK INITIALIZATION ---
    sentry_sdk.init(
        dsn=os.environ.get("SENTRY_DSN"), # Use os.environ.get for safety
        integrations=[FlaskIntegration()],
        traces_sample_rate=0.2,  # performance
        enable_tracing=True
    )
    # --- END SENTRY SDK INITIALIZATION ---

    # --- NEW LOGGER SETUP (JSON) ---
    # Remove existing handlers to avoid duplicates
    for handler in app.logger.handlers[:]:
        app.logger.removeHandler(handler)
    
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

    app.logger.setLevel(logging.INFO)  # Set app logger to INFO to capture all levels of logs
    app.logger.info('--- Iniciando aplicación Gestión Koal ---')
    app.logger.info('Modo de depuración: %s', app.debug)
    app.logger.info('Carpeta de instancia: %s', app.instance_path)
    app.logger.info('Carpeta de subidas: %s', app.config['UPLOAD_FOLDER'])
    app.logger.info('Usando base de datos en: %s', app.config['DATABASE'])
    app.logger.info('Sentry DSN configurado: %s', 'Sí' if os.environ.get("SENTRY_DSN") else 'No')
    app.logger.info('--- Aplicación lista para recibir peticiones ---')
    # --- END NEW LOGGER SETUP ---


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
    def inject_helpers():
        def can(perm: str) -> bool:
            return current_user.is_authenticated and current_user.has_permission(perm)
        return {"can": can}

    # --- NEW before_request HOOK for request_id ---
    @app.before_request
    def inject_request_id():
        g.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
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
            db = dbmod.get_db()
            if db is None:
                flash('Database connection error.', 'error')
                return redirect(url_for("auth.login"))

            try:
                total_tickets = db.execute("SELECT COUNT(id) FROM tickets").fetchone()[0]
                pending_tickets = db.execute("SELECT COUNT(id) FROM tickets WHERE estado = 'abierto'").fetchone()[0]
                pending_payments = db.execute("SELECT COUNT(id) FROM tickets WHERE estado_pago != 'Pagado'").fetchone()[0]
                total_clients = db.execute("SELECT COUNT(id) FROM clientes").fetchone()[0]
                
                tickets = db.execute(
                    "SELECT t.id, t.descripcion, t.estado, t.created_at, c.nombre as client_nombre, u.username as assigned_user_username "
                    "FROM tickets t LEFT JOIN clientes c ON t.cliente_id = c.id LEFT JOIN users u ON t.asignado_a = u.id "
                    "ORDER BY t.created_at DESC LIMIT 10"
                ).fetchall()

                return render_template(
                    "dashboard.html",
                    total_tickets=total_tickets,
                    pending_tickets=pending_tickets,
                    pending_payments=pending_payments,
                    total_clients=total_clients,
                    tickets=tickets
                )
            except Exception as e:
                app.logger.error(f"Error fetching dashboard data: {e}", exc_info=True)
                flash('Error al cargar los datos del dashboard.', 'error')
                return redirect(url_for("auth.login"))
        else:
            return redirect(url_for("auth.login"))

    # --- Health Check ---
    @app.route("/healthz")
    def health_check():
        return jsonify({"ok": True, "ts": time.time()}), 200 # Updated to match snippet

    from flask import send_from_directory

    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(os.path.join(app.root_path, 'static'),
                                   'favicon.ico', mimetype='image/vnd.microsoft.icon')

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

    dbmod.init_app(app)
    dbmod.register_commands(app)

    # Register Blueprints
    from . import auth, jobs, clients, services, materials, providers, freelancers, users, about, reports, notifications, profile, quotes, scheduled_maintenance, feedback, ai_chat, stock_movements, material_research, market_study, financial_transactions, shared_expenses, payment_confirmation, freelancer_quotes, asset_management
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
    app.register_blueprint(ai_chat.bp)
    app.register_blueprint(stock_movements.bp)
    app.register_blueprint(material_research.bp)
    app.register_blueprint(market_study.bp)
    app.register_blueprint(financial_transactions.bp)
    app.register_blueprint(shared_expenses.bp)
    app.register_blueprint(payment_confirmation.bp)
    app.register_blueprint(freelancer_quotes.bp)
    app.register_blueprint(asset_management.bp)

    return app
