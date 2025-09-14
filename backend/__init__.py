# backend/__init__.py
from flask import Flask
import os

def create_app():
    # Sirve estáticos desde carpeta /static en la raíz del repo
    app = Flask(
        __name__,
        static_folder=os.path.join(os.path.dirname(__file__), "..", "static"),
        static_url_path="/static",
    )

    @app.get("/healthz")
    def healthz():
        return "ok", 200

    @app.get("/")
    def index():
        return """
        <!doctype html>
        <html lang="es">
          <head>
            <meta charset="utf-8">
            <title>KOAL · OK</title>
            <link rel="icon" href="/static/favicon.ico">
          </head>
          <body style="font-family: system-ui; padding: 24px">
            <h1>OK: servicio en marcha</h1>
            <p>Health: <a href="/healthz">/healthz</a></p>
            <p>Static test (si existen):</p>
            <p><img src="/static/logo.jpg" alt="logo" style="max-height:80px"></p>
            <p><img src="/static/favicon.ico" alt="favicon" style="height:32px"></p>
          </body>
        </html>
        """, 200

    # Opcional: si el navegador pide /favicon.ico en raíz:
    @app.get("/favicon.ico")
    def favicon():
        return app.send_static_file("favicon.ico")

    return app