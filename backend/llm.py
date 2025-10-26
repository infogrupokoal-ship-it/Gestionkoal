# backend/llm.py
import os
import json
from flask import current_app
import google.generativeai as genai

SYSTEM_PRIMER = """Eres un asistente de coordinación de avisos para una empresa de servicios.
Devuelves SIEMPRE JSON válido y minimalista. Campos no presentes = null."""

PROMPTS = {
  "extract_client_fields": '''{primer}
Extrae si existen: nombre, email, nif. Si no hay dato, devuelve null.
Entrada: {message}
Salida JSON: {{"nombre": str|null, "email": str|null, "nif": str|null}}''',
  "triage_ticket": '''{primer}
Clasifica el aviso. Campos: tipo (categoria), prioridad (alta|media|baja), titulo (<=80 chars), descripcion.
Entrada: {message}
Salida JSON: {{"tipo": str, "prioridad": "alta"|"media"|"baja", "titulo": str, "descripcion": str}}''',
  "suggest_reply": '''{primer}
Basado en el siguiente contexto de un ticket, redacta una respuesta amable y concisa para el cliente.
Contexto: {context}
Salida JSON: {{"reply_text": str}}''',
}

def ask_gemini_json(task_key: str, vars: dict):
    # In a real scenario, you would use the configured API key
    # For now, we can use a mock response to avoid API calls during setup
    if os.getenv("GEMINI_API_KEY", "demo") == "demo":
        if task_key == "extract_client_fields":
            return {"nombre": "Cliente de Test", "email": "test@example.com", "nif": None}
        if task_key == "triage_ticket":
            return {"tipo": "electricidad", "prioridad": "media", "titulo": "Luz parpadea en el salón", "descripcion": vars.get("message")}
        return {}

    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = PROMPTS[task_key].format(primer=SYSTEM_PRIMER, **vars)
    res = model.generate_content(prompt)
    text = res.text or "{}"
    try:
        return json.loads(text)
    except Exception:
        import re
        m = re.search(r"\{.*\}", text, re.S)
        return json.loads(m.group(0)) if m else {}
