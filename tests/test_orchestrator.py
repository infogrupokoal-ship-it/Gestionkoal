import pytest

from backend.db_utils import get_db


@pytest.fixture(autouse=True)
def mock_ai_and_assignment(monkeypatch):
    def mock_ask_gemini_json(task_key, vars):
        if task_key == "extract_client_fields":
            return {"nombre": "Test Client", "email": "test@client.com", "nif": None}
        if task_key == "triage_ticket":
            return {
                "tipo": "fontaneria",
                "prioridad": "alta",
                "titulo": "Fuga de agua en el baño",
                "descripcion": vars.get("message"),
            }
        return {}

    monkeypatch.setattr("backend.ai_orchestrator.ask_gemini_json", mock_ask_gemini_json)

    def mock_suggest_assignee(db, tipo, prioridad, client_row):
        return {"id": 2, "username": "autonomo"}

    monkeypatch.setattr(
        "backend.ai_orchestrator.suggest_assignee", mock_suggest_assignee
    )

    class MockWhatsAppClient:
        def send_text(self, to_phone, text):
            return {"ok": True, "dry_run": True}

    monkeypatch.setattr("backend.ai_orchestrator.WhatsAppClient", MockWhatsAppClient)


def test_process_incoming_text_new_client_new_ticket(app):
    with app.app_context():
        db = get_db()
        db.execute("DELETE FROM clientes WHERE telefono = '34666777888'")
        db.commit()

        from backend.ai_orchestrator import process_incoming_text

        result = process_incoming_text(
            source="whatsapp",
            raw_phone="+34 666 777 888",
            text="Hola, tengo una fuga de agua en el baño de casa.",
        )

        assert result["ok"] is True
        assert result["ticket_id"] is not None

        client = db.execute(
            "SELECT * FROM clientes WHERE telefono = ?", ("34666777888",)
        ).fetchone()
        assert client is not None
        assert client["nombre"] == "Test Client"

        ticket = db.execute(
            "SELECT * FROM tickets WHERE id = ?", (result["ticket_id"],)
        ).fetchone()
        assert ticket is not None
        assert ticket["prioridad"] == "alta"
        assert ticket["estado"] == "asignado"
