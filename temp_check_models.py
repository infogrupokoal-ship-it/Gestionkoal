
import os
import sys
# Add project root to path to allow backend imports
sys.path.insert(0, os.getcwd())

from flask import Flask
from backend.models import _prepare_mappings, Base

# Create a minimal Flask app context
app = Flask(__name__, instance_relative_config=True)
app.config['DATABASE'] = os.path.join(app.instance_path, 'gestion_avisos.sqlite')

with app.app_context():
    print("Preparing to reflect database...")
    try:
        _prepare_mappings()
        print("Reflection complete.")
        print(f"Reflected tables found by automap: {list(Base.classes.keys())}")
    except Exception as e:
        print(f"An error occurred during reflection: {e}")
