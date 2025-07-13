from typing import List, Optional
from models.tag import Student, Activity, Tag

class TaggingService:
    def __init__(self):
        self.tags_cache = {}  # 缓存标签
    
    def add_tag_to_student(self, student: Student, tag: Tag) -> bool:
        try:
            if tag not in student.tags:
                student.tags.append(tag)
            return True
        except Exception:
            return False

    def add_tag_to_activity(self, activity: Activity, tag: Tag) -> bool:
        try:
            if tag not in activity.tags:
                activity.tags.append(tag)
            return True
        except Exception:
            return False

    def get_all_tags(self) -> List[Tag]:
        return list(self.tags_cache.values())

    def find_tag_by_name(self, name: str) -> Optional[Tag]:
        return self.tags_cache.get(name)
