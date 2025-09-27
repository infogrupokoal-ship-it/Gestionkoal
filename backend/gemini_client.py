# backend/gemini_client.py
import os
from typing import Optional
from flask import current_app

_CLIENT = None
_MODEL = None

def get_client(model: Optional[str] = None):
    """
    Devuelve un cliente de Gemini inicializado bajo demanda (lazy).
    Nunca se ejecuta en import de Flask ni en 'flask init-db'.
    """
    global _CLIENT, _MODEL
    if _CLIENT is not None:
        return _CLIENT

    # Usar una clave de prueba directamente para facilitar el desarrollo
    api_key = "YOUR_TEST_GEMINI_API_KEY" # Reemplazar con una clave real para pruebas
    if api_key == "YOUR_TEST_GEMINI_API_KEY":
        # Si la clave de prueba no se ha reemplazado, deshabilitar el cliente
        return None

    # Import tardío para evitar bloqueos en comandos CLI de Flask.
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    _MODEL = model or current_app.config.get("GEMINI_MODEL", "gemini-1.0-pro") # Usar un modelo de prueba por defecto
    _CLIENT = genai.GenerativeModel(_MODEL)
    return _CLIENT


def generate(prompt: str, system: str = "", temperature: float = 0.2) -> str:
    """
    Helper simple para generar texto. Devuelve string o mensaje de error legible.
    """
    client = get_client()
    if client is None:
        return "Gemini no está configurado. Define GEMINI_API_KEY (y GEMINI_MODEL opcional)."

    try:
        parts = []
        if system:
            parts.append({"role": "system", "parts": [system]})
        parts.append({"role": "user", "parts": [prompt]})
        resp = client.generate_content(
            parts,
            generation_config={"temperature": temperature}
        )
        return resp.text or "(Respuesta vacía)"
    except Exception as e:
        return f"Error al llamar a Gemini: {e}"
