# backend/similarity.py
from datetime import datetime, timedelta, timezone
from sqlalchemy import text

def simple_similarity(a: str, b: str) -> float:
    # Implementación sencilla (puedes mejorar con TF-IDF/embeddings)
    a, b = a.lower(), b.lower()
    inter = len(set(a.split()) & set(b.split()))
    base = max(len(set(a.split())), 1)
    return inter / base

def is_duplicate_of_recent(db, client_id, title, desc, within_minutes=180, threshold=0.6):
    since = datetime.now(timezone.utc) - timedelta(minutes=within_minutes)
    # In SQLite, we need to be careful with datetime formats.
    # Assuming fecha_creacion is stored in a format comparable with strings.
    since_str = since.strftime('%Y-%m-%d %H:%M:%S')
    rows = db.execute(
        text("SELECT id, titulo, descripcion FROM tickets WHERE cliente_id = :cid AND fecha_creacion >= :since"),
        {"cid": client_id, "since": since_str}
    ).fetchall()
    for r in rows:
        titulo = getattr(r, 'titulo', None) if hasattr(r, 'titulo') else r["titulo"]
        descripcion = getattr(r, 'descripcion', None) if hasattr(r, 'descripcion') else r["descripcion"]
        score = max(simple_similarity(title, titulo or ''), simple_similarity(desc, descripcion or ''))
        if score >= threshold:
            return getattr(r, 'id', None) if hasattr(r, 'id') else r["id"]
    return None
