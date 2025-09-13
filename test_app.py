from flask import Flask
import os
import sys

# Attempt to import the problematic library
try:
    import psycopg2
    import psycopg2.extras
    psycopg2_message = "psycopg2 importado correctamente."
except ImportError as e:
    psycopg2_message = f"ERROR al importar psycopg2: {e}"

# Get Python version from different sources
python_version_sys = sys.version

app = Flask(__name__)

@app.route('/')
def hello():
    return f"""
    <h1>Prueba de Entorno de Render</h1>
    <p>Hola Mundo!</p>
    <p><strong>Versión de Python (sys.version):</strong> {python_version_sys}</p>
    <p><strong>Estado de psycopg2:</strong> {psycopg2_message}</p>
    """

# This part is for local testing, Render will use the Procfile
if __name__ == '__main__':
    try:
        from waitress import serve
        serve(app, host="0.0.0.0", port=8080)
    except ImportError as e:
        print(f"ERROR al importar waitress: {e}")
        print("Por favor, ejecuta 'pip install waitress'")
