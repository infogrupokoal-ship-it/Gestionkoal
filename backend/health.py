from flask import Blueprint, jsonify

bp = Blueprint("health", __name__, url_prefix="/healthz")

@bp.route("/")
def health_check():
    """
    Health check endpoint for Render or other monitoring services.
    Returns a 200 OK status if the app is running.
    """
    return jsonify({"status": "ok"}), 200
