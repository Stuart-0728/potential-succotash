from typing import List
from models.tag import Student, Activity
from collections import Counter

class RecommendationService:
    def recommend_activities(self, student: Student, activities: List[Activity], limit: int = 10) -> List[Activity]:
        # 计算活动得分
        activity_scores = []
        for activity in activities:
            score = self._calculate_score(student, activity)
            activity_scores.append((activity, score))
        
        # 按得分排序并返回前N个
        sorted_activities = sorted(activity_scores, key=lambda x: x[1], reverse=True)
        return [activity for activity, _ in sorted_activities[:limit]]
    
    def _calculate_score(self, student: Student, activity: Activity) -> float:
        # 标签匹配得分
        tag_score = len(set(student.tags) & set(activity.tags))
        # 历史参与度得分
        history_score = sum(1 for hist in student.activity_history if hist == activity.activity_id)
        return tag_score * 0.7 + history_score * 0.3
