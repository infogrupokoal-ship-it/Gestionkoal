import sys

from backend.__init__ import create_app
from backend.db_utils import close_db, get_db

app = create_app()
app.app_context().push()

with app.app_context():
    db = get_db()
    if db is None:
        print("Error: Could not get database connection.")
        sys.exit(1)

    try:
        print("Attempting direct insert...")
        db.execute(
            "INSERT INTO tickets (cliente_id, tipo, estado, creado_por) VALUES (?, ?, ?, ?)",
            (1, "Direct Insert Test", "Pendiente", 1)
        )
        db.commit()
        print("Direct insert successful!")

    except Exception as e:
        db.rollback()
        print(f"Error during direct insert: {e}")
    finally:
        close_db()

