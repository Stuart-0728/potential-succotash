from typing import List
from datetime import datetime

class Tag:
    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name

class Student:
    def __init__(self, student_id: str, name: str, tags: List[Tag] = None):
        self.student_id = student_id
        self.name = name
        self.tags = tags or []
        self.activity_history = []

class Activity:
    def __init__(self, activity_id: str, title: str, tags: List[Tag] = None):
        self.activity_id = activity_id
        self.title = title
        self.tags = tags or []
        self.created_at = datetime.now()
