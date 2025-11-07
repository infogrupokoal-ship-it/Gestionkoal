import json

from backend.llm import ask_gemini_json


def sugerir_materiales_servicios(descripcion):
    # La lógica del prompt ahora está definida en backend/llm.py bajo la task_key "catalogo_materiales_servicios"
    respuesta = ask_gemini_json("catalogo_materiales_servicios", {"descripcion": descripcion})
    try:
        # ask_gemini_json ya debería devolver un dict si tiene éxito
        if isinstance(respuesta, str):
            return json.loads(respuesta)
        return respuesta
    except Exception as e:
        print("Error procesando respuesta de Gemini en sugerir_materiales_servicios:", e)
        return None
