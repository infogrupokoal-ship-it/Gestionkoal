from backend.whatsapp_templates import render_template


# backend/rules_engine.py
def evaluate_policies(client, context):
    """
    Devuelve dict con:
    - auto_assign: bool
    - reply_template: str
    - reply_key: str (opcional, clave de plantilla)
    - sla_hours: int (opcional, si quieres personalizar SLA)
    """
    prio = (context.get("prioridad") or "media").lower()

    auto = True if prio == "alta" else False

    if prio == "alta":
        key = "ack_high"
    elif prio == "baja":
        key = "ack_low"
    else:
        key = "ack_medium"

    reply = render_template(key)

    return {"auto_assign": auto, "reply_template": reply, "reply_key": key}
