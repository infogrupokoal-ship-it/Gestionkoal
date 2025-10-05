# backend/metrics.py
import sqlite3
from typing import Any

# Sinónimos por categoría
PENDING_STATES = {"pendiente", "pendientes", "nuevo", "nueva", "pendiente_asignacion", "por_asignar", "por_programar"}
IN_PROGRESS_STATES = {"en_curso", "progreso", "en_progreso", "asignado", "programado"}
DONE_STATES = {"completado", "finalizado", "cerrado", "hecho"}
CANCELLED_STATES = {"cancelado", "anulado", "rechazado"}

TABLE_CANDIDATES = ("trabajos", "jobs", "tickets")
STATUS_COL_CANDIDATES = ("estado", "status", "estado_trabajo")

def _detect_table_and_status_column(conn: sqlite3.Connection) -> tuple[str, str]:
    cur = conn.cursor()
    # Detectar tabla
    cur.execute(
        f"SELECT name FROM sqlite_master WHERE type='table' AND name IN ({','.join(['?']*len(TABLE_CANDIDATES))})",
        TABLE_CANDIDATES
    )
    row = cur.fetchone()
    if not row:
        # Por compatibilidad con instalaciones limpias de test, creamos una tabla mínima
        table = "trabajos"
        cur.execute("CREATE TABLE IF NOT EXISTS trabajos (id INTEGER PRIMARY KEY, estado TEXT)")
    else:
        table = row[0]

    # Detectar columna de estado
    cur.execute(f"PRAGMA table_info({table})")
    cols = {r[1].lower(): r[1] for r in cur.fetchall()}  # {lower_name: real_name}
    status_col_real = None
    for cand in STATUS_COL_CANDIDATES:
        if cand in cols:
            status_col_real = cols[cand]
            break

    if not status_col_real:
        # Añadir columna estado si no existe (modo defensivo)
        cur.execute(f"ALTER TABLE {table} ADD COLUMN estado TEXT")
        status_col_real = "estado"

    # Índice para rendimiento
    cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_{status_col_real} ON {table}({status_col_real})")

    conn.commit()
    return table, status_col_real

def _count_by_values(conn: sqlite3.Connection, table: str, col: str, values: list[str]) -> int:
    if not values:
        return 0
    placeholders = ",".join(["?"] * len(values))
    sql = f"SELECT COUNT(*) FROM {table} WHERE LOWER({col}) IN ({placeholders})"
    cur = conn.cursor()
    cur.execute(sql, [v.lower() for v in values])
    return int(cur.fetchone()[0])

def get_dashboard_kpis(conn: sqlite3.Connection) -> dict[str, Any]:
    table, status_col = _detect_table_and_status_column(conn)

    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    total = int(cur.fetchone()[0])

    pendientes = _count_by_values(conn, table, status_col, list(PENDING_STATES))
    en_curso = _count_by_values(conn, table, status_col, list(IN_PROGRESS_STATES))
    completados = _count_by_values(conn, table, status_col, list(DONE_STATES))
    cancelados = _count_by_values(conn, table, status_col, list(CANCELLED_STATES))

    return {
        "table": table,
        "status_field": status_col,
        "total": total,
        "pendientes": pendientes,
        "en_curso": en_curso,
        "completados": completados,
        "cancelados": cancelados,
        # Derivados útiles
        "abiertos": total - completados - cancelados,
    }
