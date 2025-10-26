# backend/assignment.py
def suggest_assignee(db, tipo, prioridad, client_row):
    # Heurística inicial: rol/especialidad + menos carga
    # Necesita tabla skills o mapping; por ahora demo:
    # This query is a placeholder and will likely fail without a user_skills table.
    # We will return a mock user for now.
    # row = db.execute(
    #     "SELECT u.id, u.username FROM users u "
    #     "LEFT JOIN user_skills s ON u.id=s.user_id "
    #     "WHERE (s.skill = ? OR s.skill IS NULL) AND u.role IN ('tecnico','autonomo') "
    #     "ORDER BY (SELECT COUNT(*) FROM tickets t WHERE t.asignado_a=u.id AND t.estado IN ('nuevo','asignado')) ASC LIMIT 1",
    #     (tipo,)
    # ).fetchone()
    # return row  # {id, username}
    
    # Mock response to avoid DB errors until user_skills is defined
    return {"id": 1, "username": "admin"} # Assuming user with id 1 exists
