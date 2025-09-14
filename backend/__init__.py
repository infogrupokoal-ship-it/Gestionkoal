# backend/__init__.py
from flask import Flask

def create_app():
    app = Flask(__name__)

    @app.get("/healthz")
    def healthz():
        return "ok", 200

    return app