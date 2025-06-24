from src import create_app

app = create_app()

print('URL规则:')
with app.app_context():
    for rule in app.url_map.iter_rules():
        if 'checkin_modal' in str(rule):
            print(f'规则: {rule}, 终点: {rule.endpoint}') 