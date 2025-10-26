# backend/jobs_sla.py
from datetime import datetime, timedelta
from backend.db_utils import get_db
from backend.whatsapp import WhatsAppClient
import dateutil.parser

def run_sla_checker():
    db = get_db()
    now = datetime.utcnow()
    rows = db.execute(
        "SELECT id, cliente_id, titulo, sla_due FROM tickets WHERE estado IN ('nuevo','asignado')"
    ).fetchall()
    for r in rows:
        due = r["sla_due"]
        if not due: continue
        
        try:
            due_dt = dateutil.parser.isoparse(due)
            delta = (due_dt - now).total_seconds()
            
            if 0 < delta <= 900: # 15 minutes
                # Check if a warning has been sent recently to avoid spam
                last_event = db.execute(
                    "SELECT created_at FROM sla_events WHERE ticket_id = ? AND event = 'warn' ORDER BY created_at DESC LIMIT 1", (r["id"],)
                ).fetchone()
                if not last_event or (now - dateutil.parser.isoparse(last_event['created_at'])) > timedelta(minutes=10):
                    db.execute("INSERT INTO sla_events (ticket_id, event, details) VALUES (?,?,?)",
                               (r["id"], "warn", "SLA due in <15min"))
                    db.commit()
                    # Optionally, notify someone
            elif delta <= 0:
                # Check if a breach event already exists
                breach_event = db.execute("SELECT id FROM sla_events WHERE ticket_id = ? AND event = 'breach'", (r["id"],)).fetchone()
                if not breach_event:
                    db.execute("INSERT INTO sla_events (ticket_id, event, details) VALUES (?,?,?)",
                               (r["id"], "breach", "SLA breached"))
                    db.commit()
                    # Optionally, escalate
        except (ValueError, TypeError):
            # Handle cases where sla_due is not a valid ISO format string
            continue
