import os, json, datetime as dt
import requests  # para leer de tu proveedor de logs (ej: Logtail API)
from google import genai
from google.genai import types as gt

GENAI_API_KEY = os.environ["GEMINI_API_KEY"]
client = genai.Client(api_key=GENAI_API_KEY)

# Esquema de salida para obligar a JSON válido (structured output)
Action = gt.Schema(
    type=gt.Type.OBJECT,
    properties={
        "severity": gt.Schema(type=gt.Type.STRING, enum=["INFO","WARN","ERROR","CRITICAL"]),
        "root_cause": gt.Schema(type=gt.Type.STRING),
        "customer_message": gt.Schema(type=gt.Type.STRING),
        "engineer_actions": gt.Schema(type=gt.Type.ARRAY, items=gt.Schema(type=gt.Type.STRING)),
        "should_page_oncall": gt.Schema(type=gt.Type.BOOLEAN),
        "runbooks": gt.Schema(type=gt.Type.ARRAY, items=gt.Schema(type=gt.Type.STRING)),
        "tool_calls": gt.Schema(type=gt.Type.ARRAY, items=gt.Schema(type=gt.Type.OBJECT, properties={
            "name": gt.Schema(type=gt.Type.STRING),
            "args": gt.Schema(type=gt.Type.OBJECT)
        }))
    },
    required=["severity","root_cause","engineer_actions","should_page_oncall"]
)

def fetch_logs_since(minutes=5):
    log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance", "error.log")
    if not os.path.exists(log_file_path):
        return []

    # Read logs from the file
    entries = []
    with open(log_file_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line)
                # Filter by timestamp if needed, but for now, just parse
                entries.append(entry)
            except json.JSONDecodeError:
                # Handle malformed JSON lines
                pass
    return entries

def analyze_with_gemini(entries):
    prompt = (
      "Eres un SRE para una app Flask en Render. "
      "Clasifica y propone acciones. Devuelve JSON valido según schema."
    )
    content = [
        gt.Content(role="user", parts=[gt.Part.from_text(prompt),
                                       gt.Part.from_text(json.dumps(entries)[:100000])])
    ]
    resp = client.models.generate_content(
        model="gemini-2.0-flash",  # rápido y barato para vigilancia
        contents=content,
        config=gt.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=Action
        )
    )
    return json.loads(resp.text)

def main():
    entries = fetch_logs_since(5)
    if not entries: 
        return
    result = analyze_with_gemini(entries)
    # Ejecuta tool_calls (function calling) según lo que devuelva Gemini:
    for call in result.get("tool_calls", []):
        if call["name"] == "create_github_issue":
            # llama a tu GitHub API...
            pass
        if call["name"] == "notify_whatsapp":
            # Twilio / WhatsApp...
            pass
    # Guarda resumen en tu DB y envía mensaje al canal de soporte

if __name__ == "__main__":
    main()