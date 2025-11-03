import csv
import io

from flask import Blueprint, Response, current_app, render_template, request
from sqlalchemy import text

from backend.extensions import db

bp = Blueprint("twilio_wa", __name__, url_prefix="/whatsapp")


@bp.route("/logs")
def list_whatsapp_logs():
    status = (request.args.get("status") or "").strip()
    q = (request.args.get("q") or "").strip()
    try:
        base_sql = "SELECT id, whatsapp_message_id, status, timestamp, from_number FROM whatsapp_message_logs"
        where = []
        params = {}
        if status:
            where.append("status = :status")
            params["status"] = status
        if q:
            where.append("from_number LIKE :q")
            params["q"] = f"%{q}%"
        if where:
            base_sql += " WHERE " + " AND ".join(where)
        base_sql += " ORDER BY id DESC"
        rows = db.session.execute(text(base_sql), params).fetchall()
    except Exception:
        current_app.logger.warning(
            "Failed to read whatsapp_message_logs; falling back to empty list",
            exc_info=True,
        )
        rows = []

    def mask(num: str | None) -> str:
        if not num:
            return ""
        last4 = num[-4:]
        return f"***{last4}"

    logs = [
        {
            "id": r.id,
            "message_id": getattr(r, "whatsapp_message_id", None),
            "status": getattr(r, "status", None),
            "timestamp": getattr(r, "timestamp", None),
            "from_number_hash": mask(getattr(r, "from_number", None)),
        }
        for r in rows
    ]
    # Export CSV if requested
    if (request.args.get("export") or "").lower() == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "message_id", "status", "timestamp", "from_number"])
        for r in rows:
            writer.writerow(
                [
                    getattr(r, "id", ""),
                    getattr(r, "whatsapp_message_id", ""),
                    getattr(r, "status", ""),
                    getattr(r, "timestamp", ""),
                    mask(getattr(r, "from_number", "")),
                ]
            )
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=whatsapp_logs.csv"},
        )

    # Pagination
    try:
        page = max(1, int(request.args.get("page", "1")))
    except Exception:
        page = 1
    try:
        per_page = max(1, min(200, int(request.args.get("per_page", "50"))))
    except Exception:
        per_page = 50
    total = len(logs)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    logs_page = logs[start_idx:end_idx]

    return render_template(
        "whatsapp_message_logs/list.html",
        logs=logs_page,
        status=status,
        q=q,
        page=page,
        per_page=per_page,
        total=total,
    )
