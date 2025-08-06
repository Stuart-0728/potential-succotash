import sys
sys.path.insert(0, 'src')
from src import create_app
from flask import url_for

app = create_app()
with app.app_context():
    url = url_for('admin.toggle_checkin', id=1)
    print(f"Generated URL: {url}")