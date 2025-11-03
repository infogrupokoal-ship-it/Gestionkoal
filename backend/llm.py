# backend/llm.py
import json
import os

import google.generativeai as genai

SYSTEM_PRIMER = """Eres un asistente de coordinación de avisos para una empresa de servicios.
Devuelves SIEMPRE JSON válido y minimalista. Campos no presentes = null."""

PROMPTS = {
    "extract_client_fields": """{primer}
Extrae si existen: nombre, email, nif. Si no hay dato, devuelve null.
Entrada: {message}
Salida JSON: {{"nombre": str|null, "email": str|null, "nif": str|null}}""",
    "triage_ticket": """{primer}
Clasifica el aviso. Campos: tipo (categoria), prioridad (alta|media|baja), titulo (<=80 chars), descripcion.
Entrada: {message}
Salida JSON: {{"tipo": str, "prioridad": "alta"|"media"|"baja", "titulo": str, "descripcion": str}}""",
    "suggest_reply": """{primer}
Basado en el siguiente contexto de un ticket, redacta una respuesta amable y concisa para el cliente.
Contexto: {context}
Salida JSON: {{"reply_text": str}}""",
    "catalogo_materiales_servicios": """{primer}
Actúa como un asesor técnico experto en mantenimiento y reparaciones del hogar y edificios, y como un analista de mercado. Necesito que generes un objeto JSON con dos claves: 'materiales' y 'servicios'.

Genera al menos 30 elementos para la lista de 'materiales' y al menos 30 elementos para la lista de 'servicios'. Asegúrate de que los datos sean realistas y variados, cubriendo diferentes categorías y tipos de trabajos comunes en el sector.

Cada elemento de 'materiales' debe contener las siguientes claves con valores realistas:
  - nombre (str)
  - descripcion (str)
  - categoria (str)
  - precio_costo_estimado (float)
  - precio_venta_sugerido (float)
  - unidad_medida (str)
  - proveedor_sugerido (str)
  - stock_minimo (int)
  - tiempo_entrega_dias (int)
  - observaciones (str)

Cada elemento de 'servicios' debe contener las siguientes claves con valores realistas:
  - nombre (str)
  - descripcion (str)
  - categoria (str)
  - precio_base_estimado (float)
  - unidad_medida (str)
  - tiempo_estimado_horas (float)
  - habilidades_requeridas (str)
  - observaciones (str)

La salida debe ser estrictamente un objeto JSON válido, sin ningún texto adicional antes o después del JSON.
""",
}


def ask_gemini_json(task_key: str, vars: dict):
    # In a real scenario, you would use the configured API key
    # For now, we can use a mock response to avoid API calls during setup
    if os.getenv("GEMINI_API_KEY", "demo") == "demo":
        from backend.gemini_mock import get_mock_response # Import the mock responses

        mock_response = get_mock_response(task_key, vars)
        if mock_response is not None:
            return mock_response
        # Fallback for other task_keys if no specific mock is defined
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
