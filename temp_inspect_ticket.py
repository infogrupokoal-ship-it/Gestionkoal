from backend import create_app
from backend.models import get_table_class

app = create_app()
with app.app_context():
    Ticket = get_table_class('tickets')
    print(dir(Ticket))
