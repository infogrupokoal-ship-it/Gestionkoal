# backend/__init__.py
from flask import Flask

def create_app():
    app = Flask(__name__)

    @app.get("/healthz")
    def healthz():
        return "ok", 200

    @app.get("/")
    def index():
        # Página súper simple para verificar que todo responde y que static sigue ahí
        return """
    <!doctype html>
    <html lang="es">
      <head><meta charset="utf-8"><title>KOAL · OK</title></head>
      <body style="font-family: system-ui; padding: 24px">
        <h1>OK: servicio en marcha</h1>
        <p>Health: <a href="/healthz">/healthz</a></p>
        <p>Static test (si existe tu logo antiguo):</p>
        <p><img src="/static/logo.png" alt="logo" style="max-height:80px"></p>
        <p><img src="/static/favicon.ico" alt="favicon" style="height:32px"></p>
      </body>
    </html>
    """, 200

    return app