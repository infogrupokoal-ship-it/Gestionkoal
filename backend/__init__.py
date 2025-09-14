# backend/__init__.py
from flask import Flask
import os

def create_app():
    try:
        app = Flask(__name__, instance_relative_config=True)
        app.config.from_mapping(
            SECRET_KEY=os.environ.get("SECRET_KEY", "dev"),
            DATABASE=os.environ.get("DATABASE_PATH", os.path.join(app.instance_path, "gestion_avisos.sqlite")),
        )

        @app.route("/")
        def index():
            return "OK: gestion_avisos running"

        return app
    except Exception as e:
        import sys
        import traceback
        print(f"Error in create_app: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        raise