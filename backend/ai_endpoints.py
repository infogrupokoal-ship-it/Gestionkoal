from flask import Blueprint, request, jsonify, current_app
import json

# Suponiendo que tienes un cliente Gemini configurado en alguna parte
# from . import gemini_client 
# from .auth import login_required

ai_endpoints_bp = Blueprint('ai_endpoints', __name__, url_prefix='/api')

# El prompt final que acordamos
SUGGESTION_PROMPT_TEMPLATE = """
[INICIO DEL PROMPT]

### ROL Y OBJETIVO
Eres un asistente de inteligencia comercial para "Gestionkoal". Tu objetivo es sugerir el socio comercial (rol "comercial") más adecuado para un nuevo trabajo, basándote en un análisis de los datos proporcionados.

### CRITERIOS DE EVALUACIÓN
Debes basar tu recomendación en los siguientes criterios, en orden de importancia:
1.  **Especialidad**: Coincidencia entre el tipo/descripción del trabajo y las especialidades/historial del comercial.
2.  **Geografía**: Proximidad entre la ubicación del trabajo y la zona de operación del comercial.
3.  **Rentabilidad**: Historial de rentabilidad del comercial en trabajos anteriores.
4.  **Tipo de Cliente**: Experiencia previa del comercial con clientes similares (particulares, empresas).

### CONTEXTO (DATOS DE ENTRADA)

**1. Datos del Nuevo Trabajo:**
```json
{
  "descripcion": "{descripcion}",
  "tipo_servicio": "{tipo_servicio}",
  "direccion": "{direccion}",
  "tipo_cliente": "{tipo_cliente}"
}
```

**2. Datos de Socios Comerciales Disponibles:**
```json
{comerciales_json}
```

### TAREA Y FORMATO DE SALIDA

Analiza los datos y responde **únicamente con un objeto JSON válido** que siga esta estructura:

- `sugerido`: Objeto con `id` y `nombre` del comercial más recomendable.
- `alternativas`: Array de hasta 2 alternativas, ordenadas por preferencia. Cada una con `id`, `nombre` y `confianza` (1-5).
- `justificacion`: Breve explicación de por qué el `sugerido` es la mejor opción.
- `confianza`: Nivel de confianza global (1-5) para la recomendación principal.

**Ejemplo de Salida Exitosa:**
```json
{
  "sugerido": { "id": 42, "nombre": "María Fernández" },
  "alternativas": [
    { "id": 31, "nombre": "Carlos Ríos", "confianza": 4 }
  ],
  "justificacion": "María Fernández es la opción principal por su especialidad directa en 'electricidad' y su experiencia con 'empresas'. Carlos Ríos es una buena alternativa por su ubicación.",
  "confianza": 5
}
```

**Si no hay datos suficientes o ningún candidato es adecuado:**
```json
{
  "sugerido": null,
  "alternativas": [],
  "justificacion": "No hay datos suficientes o ningún comercial con la especialidad requerida en la zona especificada.",
  "confianza": 1
}
```
[FIN DEL PROMPT]
"""

@ai_endpoints_bp.route('/suggest-partner', methods=['POST'])
# @login_required # Descomentar cuando se integre la autenticación
def suggest_partner():
    """
    Recibe los detalles de un trabajo y una lista de comerciales,
    y devuelve una sugerencia de asignación generada por IA.
    """
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    
    # Validación de datos de entrada
    required_fields = ['descripcion', 'tipo_servicio', 'direccion', 'tipo_cliente', 'comerciales']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    # Formatear los datos para el prompt
    try:
        comerciales_json_str = json.dumps(data['comerciales'], indent=2)
        
        full_prompt = SUGGESTION_PROMPT_TEMPLATE.format(
            descripcion=data['descripcion'],
            tipo_servicio=data['tipo_servicio'],
            direccion=data['direccion'],
            tipo_cliente=data['tipo_cliente'],
            comerciales_json=comerciales_json_str
        )
    except Exception as e:
        current_app.logger.error(f"Error formateando el prompt: {e}")
        return jsonify({"error": "Internal server error formatting prompt"}), 500

    # --- Llamada a la API de Gemini ---
    try:
        # Importar el cliente de Gemini aquí para evitar dependencias circulares
        from . import gemini_client

        ai_response_str = gemini_client.generate_text_from_prompt(full_prompt)
        
        # Limpiar y parsear la respuesta de la IA
        # A veces la IA puede devolver el JSON dentro de un bloque de código markdown
        if ai_response_str.strip().startswith("```json"):
            ai_response_str = ai_response_str.strip()[7:-4]
        elif ai_response_str.strip().startswith("```"):
            ai_response_str = ai_response_str.strip()[3:-3]
            
        suggestion = json.loads(ai_response_str.strip())
        
        # --- Registrar el log en la base de datos ---
        try:
            from .extensions import db
            from .models import get_table_class
            AiSuggestionLog = get_table_class('ai_suggestion_logs')
            
            new_log = AiSuggestionLog(
                user_id=g.user.id if hasattr(g, 'user') and g.user.is_authenticated else None,
                prompt_sent=full_prompt,
                response_received=ai_response_str,
                confidence_score=suggestion.get('confianza'),
                model_used=current_app.config.get("GEMINI_MODEL")
            )
            db.session.add(new_log)
            db.session.commit()
        except Exception as log_e:
            current_app.logger.error(f"Error al guardar el log de la sugerencia de IA: {log_e}")
            # No fallar la petición principal si el log falla
            db.session.rollback()

        return jsonify(suggestion), 200

    except json.JSONDecodeError:
        current_app.logger.error(f"Error decodificando JSON de la respuesta de la IA: {ai_response_str}")
        return jsonify({"error": "Failed to decode AI response"}), 500
    except Exception as e:
        current_app.logger.error(f"Error llamando a la API de IA: {e}")
        return jsonify({"error": "An unexpected error occurred with the AI service"}), 500