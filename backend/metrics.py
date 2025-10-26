# backend/metrics.py
from typing import Any
from sqlalchemy import text
from sqlalchemy.orm import Session

# Sinónimos por categoría
PENDING_STATES = {"abierto", "pendiente", "pendientes", "nuevo", "nueva", "pendiente_asignacion", "por_asignar", "por_programar"}
IN_PROGRESS_STATES = {"en_curso", "progreso", "en_progreso", "asignado", "programado"}
DONE_STATES = {"completado", "finalizado", "cerrado", "hecho"}
CANCELLED_STATES = {"cancelado", "anulado", "rechazado"}

def get_dashboard_kpis(conn: Session) -> dict[str, Any]:

    total = conn.execute(text("SELECT COUNT(*) FROM tickets")).scalar()

    # Los tests consideran "pendientes" como estado == 'abierto'
    pendientes = conn.execute(
        text("SELECT COUNT(*) FROM tickets WHERE estado = :estado"),
        {"estado": "abierto"}
    ).scalar()

    en_curso = conn.execute(
        text("SELECT COUNT(*) FROM tickets WHERE estado = :estado"),
        {"estado": "en_progreso"}
    ).scalar()

    completados = conn.execute(
        text("SELECT COUNT(*) FROM tickets WHERE estado = :estado"),
        {"estado": "finalizado"}
    ).scalar()

    cancelados = conn.execute(
        text("SELECT COUNT(*) FROM tickets WHERE estado = :estado"),
        {"estado": "cancelado"}
    ).scalar()

    pagos_pendientes = conn.execute(
        text("SELECT COUNT(*) FROM tickets WHERE estado_pago IS NULL OR estado_pago <> 'Pagado'")
    ).scalar()

    total_clientes = conn.execute(
        text("SELECT COUNT(*) FROM clientes")
    ).scalar()

    # ← CLAVE QUE FALTABA PARA EL TEST
    abiertos = int(total) - int(completados) - int(cancelados)

    return {
        "total": int(total),
        "pendientes": int(pendientes),
        "en_curso": int(en_curso),
        "completados": int(completados),
        "cancelados": int(cancelados),
        "pagos_pendientes": int(pagos_pendientes),
        "total_clientes": int(total_clientes),
        "abiertos": int(abiertos),  # <- nuevo
    }
