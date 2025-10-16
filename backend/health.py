from flask import Blueprint, jsonify

bp = Blueprint("health", __name__)

@bp.get("/health")
def health():
    return jsonify(status="ok"), 200

@bp.get("/version")
def version():
    # Placeholder version, ideally this would come from a commit hash or config
    return jsonify(version="0.1.0"), 200