import sys
sys.path.insert(0, 'src')
from src import create_app
from flask import url_for

app = create_app()
with app.test_request_context():
    url = url_for('admin.toggle_checkin', id=1)
    print(f'Generated URL: {url}')
    
    # 检查URL是否包含toggle-checkin
    if 'toggle-checkin' in url:
        print('✓ URL contains toggle-checkin')
    else:
        print('✗ URL does not contain toggle-checkin')
        
    print(f'URL parts: {url.split("/")}')