import os
import sys
from flask import Flask, g, request
from backend.db import get_db, close_db
from backend.__init__ import create_app
from backend.jobs import add_job # Import the add_job function

# Create a dummy app context
app = create_app()
app.app_context().push()

# Mock g.user
class MockUser:
    def __init__(self, user_id):
        self.id = user_id

with app.app_context():
    # Set up a dummy user in g
    g.user = MockUser(1) # Assuming user with ID 1 exists (admin)

    # Simulate request context with minimal form data
    with app.test_request_context(data={
        'client_id': '1',
        'titulo': 'Trabajo Mínimo',
        'estado': 'Pendiente',
    }):
        try:
            # Call the add_job function directly
            response = add_job()
            print(f"add_job function returned: {response}")
            # Check for flashed messages if any
            with app.test_request_context(): # Need a new context for flashed messages
                for category, message in app.get_flashed_messages(with_categories=True):
                    print(f"Flashed message ({category}): {message}")

        except Exception as e:
            print(f"An unexpected error occurred during add_job: {e}")
        finally:
            close_db()

