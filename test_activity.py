from src import create_app
from src.models import db, Activity

app = create_app()

with app.app_context():
    try:
        activity = db.get_or_404(Activity, 2)
        print(f"Activity ID: {activity.id}")
        print(f"Title: {activity.title}")
        print(f"Poster: {activity.poster_image}")
        print(f"Tags: {[tag.name for tag in activity.tags]}")
    except Exception as e:
        print(f"Error: {e}") 