from flask import Blueprint, jsonify, current_app
from backend.extensions import db # Import the global db instance
from sqlalchemy.exc import OperationalError
from sqlalchemy import text # Import text

bp = Blueprint("health", __name__, url_prefix="/healthz")

@bp.route("/", methods=["GET"])
@bp.route("", methods=["GET"])
def health_check():
    """
    Health check endpoint for Render or other monitoring services.
    Returns a 200 OK status if the app is running and DB is accessible.
    """
    db_status = "ok"
    try:
        # Attempt a simple query to check DB connection
        db.session.execute(text("SELECT 1")).scalar()
    except OperationalError:
        db_status = "error"
        current_app.logger.error("Database connection failed during health check.")
    except Exception as e:
        db_status = "error"
        current_app.logger.error(f"Unexpected error during DB health check: {e}")

    return jsonify({"status": "ok", "db": db_status}), 200
