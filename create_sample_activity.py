#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from datetime import datetime, timedelta

# 添加应用路径到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 设置环境变量
os.environ.setdefault('FLASK_CONFIG', 'development')

from src import create_app, db
from src.models import Activity, User
from src.utils.time_helpers import get_localized_now

def create_sample_activity():
    """创建示例活动"""
    app = create_app()
    
    with app.app_context():
        try:
            # 获取当前北京时间
            now = get_localized_now()
            
            # 创建示例活动
            activity = Activity(
                title="教学技能提升工作坊",
                description="""
                <p>本次工作坊将邀请资深教育专家，为师范生提供实用的教学技能培训。</p>
                <p><strong>活动内容包括：</strong></p>
                <ul>
                    <li>课堂管理技巧</li>
                    <li>互动教学方法</li>
                    <li>教学设计原理</li>
                    <li>学生评价策略</li>
                </ul>
                <p>通过理论讲解和实践演练相结合的方式，帮助参与者提升教学能力。</p>
                """,
                requirements="""
                <p><strong>参与要求：</strong></p>
                <ul>
                    <li>师范专业在校学生</li>
                    <li>对教学技能提升有兴趣</li>
                    <li>能够全程参与活动</li>
                    <li>请携带笔记本和笔</li>
                </ul>
                """,
                rewards="""
                <p><strong>活动收获：</strong></p>
                <ul>
                    <li>获得2个学分积分</li>
                    <li>颁发参与证书</li>
                    <li>获得教学资料包</li>
                    <li>建立师生交流群</li>
                </ul>
                """,
                location="重庆师范大学教学楼A301",
                start_time=now + timedelta(days=3, hours=2),  # 3天后的上午10点
                end_time=now + timedelta(days=3, hours=5),    # 3天后的下午1点
                registration_deadline=now + timedelta(days=2), # 2天后截止报名
                max_participants=50,
                type="workshop",
                status="active",
                created_at=now,
                updated_at=now,
                credits=2
            )
            
            # 添加到数据库
            db.session.add(activity)
            db.session.commit()
            
            print(f"✅ 成功创建示例活动:")
            print(f"   活动ID: {activity.id}")
            print(f"   标题: {activity.title}")
            print(f"   开始时间: {activity.start_time}")
            print(f"   结束时间: {activity.end_time}")
            print(f"   地点: {activity.location}")
            print(f"   状态: {activity.status}")
            
            return activity.id
            
        except Exception as e:
            print(f"❌ 创建示例活动失败: {e}")
            db.session.rollback()
            return None

def create_another_sample_activity():
    """创建另一个示例活动（明天的活动）"""
    app = create_app()
    
    with app.app_context():
        try:
            # 获取当前北京时间
            now = get_localized_now()
            
            # 创建明天的示例活动
            activity = Activity(
                title="师范生职业规划讲座",
                description="""
                <p>邀请知名教育行业专家，为师范生分享职业发展经验和规划建议。</p>
                <p><strong>讲座主题：</strong></p>
                <ul>
                    <li>教育行业发展趋势</li>
                    <li>教师职业发展路径</li>
                    <li>求职面试技巧</li>
                    <li>个人品牌建设</li>
                </ul>
                <p>帮助师范生明确职业方向，制定合理的职业规划。</p>
                """,
                requirements="""
                <p><strong>参与要求：</strong></p>
                <ul>
                    <li>师范专业大三、大四学生优先</li>
                    <li>对职业规划有需求</li>
                    <li>准备个人简历（可选）</li>
                </ul>
                """,
                rewards="""
                <p><strong>活动收获：</strong></p>
                <ul>
                    <li>获得1.5个学分积分</li>
                    <li>获得职业规划指导</li>
                    <li>建立行业人脉</li>
                    <li>获得求职资料包</li>
                </ul>
                """,
                location="重庆师范大学大学城校区学术报告厅",
                start_time=now + timedelta(days=1, hours=6),  # 明天下午2点
                end_time=now + timedelta(days=1, hours=8),    # 明天下午4点
                registration_deadline=now + timedelta(hours=12), # 12小时后截止报名
                max_participants=200,
                type="lecture",
                status="active",
                created_at=now,
                updated_at=now,
                credits=1.5
            )
            
            # 添加到数据库
            db.session.add(activity)
            db.session.commit()
            
            print(f"✅ 成功创建第二个示例活动:")
            print(f"   活动ID: {activity.id}")
            print(f"   标题: {activity.title}")
            print(f"   开始时间: {activity.start_time}")
            print(f"   结束时间: {activity.end_time}")
            print(f"   地点: {activity.location}")
            print(f"   状态: {activity.status}")
            
            return activity.id
            
        except Exception as e:
            print(f"❌ 创建第二个示例活动失败: {e}")
            db.session.rollback()
            return None

if __name__ == "__main__":
    print("🚀 开始创建示例活动...")
    
    # 创建第一个示例活动
    activity_id_1 = create_sample_activity()
    
    # 创建第二个示例活动
    activity_id_2 = create_another_sample_activity()
    
    if activity_id_1 and activity_id_2:
        print(f"\n🎉 所有示例活动创建成功！")
        print(f"可以访问以下链接查看活动详情和天气卡片：")
        print(f"活动1: http://127.0.0.1:5002/student/activity/{activity_id_1}")
        print(f"活动2: http://127.0.0.1:5002/student/activity/{activity_id_2}")
    else:
        print(f"\n❌ 部分活动创建失败，请检查错误信息")
