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
os.environ.setdefault('OPENWEATHER_API_KEY', '8091ce90ee692da18471b3961900b431')

from src import create_app, db
from src.models import User, Activity
from src.utils.time_helpers import get_localized_now
from werkzeug.security import generate_password_hash

def create_test_user_and_activity():
    """创建测试用户和示例活动"""
    app = create_app()
    
    with app.app_context():
        try:
            # 检查是否已存在测试用户
            test_user = User.query.filter_by(username='testuser').first()
            if not test_user:
                # 创建测试用户
                test_user = User(
                    username='testuser',
                    email='test@example.com',
                    password_hash=generate_password_hash('123456'),
                    student_id='2023001001',
                    real_name='测试用户',
                    phone='13800138000',
                    role='student',
                    is_active=True
                )
                db.session.add(test_user)
                print("✅ 创建测试用户成功")
                print("   用户名: testuser")
                print("   密码: 123456")
            else:
                print("✅ 测试用户已存在")
            
            # 获取当前北京时间
            now = get_localized_now()
            
            # 检查是否已存在测试活动
            test_activity = Activity.query.filter_by(title='天气卡片测试活动').first()
            if not test_activity:
                # 创建测试活动（明天的活动，这样能看到天气预报）
                tomorrow = now + timedelta(days=1)
                test_activity = Activity(
                    title="天气卡片测试活动",
                    description="""
                    <p>这是一个用于测试天气卡片功能的示例活动。</p>
                    <p><strong>活动特色：</strong></p>
                    <ul>
                        <li>展示重庆当地天气信息</li>
                        <li>现代化天气卡片设计</li>
                        <li>专业天气图标显示</li>
                        <li>实时温度和湿度数据</li>
                    </ul>
                    <p>通过这个活动，您可以看到我们全新设计的天气卡片效果！</p>
                    """,
                    requirements="""
                    <p><strong>参与要求：</strong></p>
                    <ul>
                        <li>无特殊要求</li>
                        <li>欢迎所有用户参与测试</li>
                    </ul>
                    """,
                    type='讲座',
                    location='重庆市大足区XXX教学中心小学',
                    start_time=tomorrow.replace(hour=14, minute=0, second=0, microsecond=0),
                    end_time=tomorrow.replace(hour=16, minute=0, second=0, microsecond=0),
                    registration_deadline=tomorrow.replace(hour=12, minute=0, second=0, microsecond=0),
                    max_participants=50,
                    status='active',
                    poster_image='banner1.jpg',
                    created_by=test_user.id
                )
                db.session.add(test_activity)
                print("✅ 创建测试活动成功")
                print(f"   活动时间: {test_activity.start_time}")
            else:
                print("✅ 测试活动已存在")
            
            db.session.commit()
            print("\n🎉 测试数据创建完成！")
            print("\n📋 登录信息:")
            print("   URL: http://127.0.0.1:5003/auth/login")
            print("   用户名: testuser")
            print("   密码: 123456")
            print("\n🌤️ 天气卡片测试:")
            print("   登录后访问活动详情页面即可看到天气卡片")
            
        except Exception as e:
            print(f"❌ 创建测试数据失败: {e}")
            db.session.rollback()

if __name__ == "__main__":
    create_test_user_and_activity()
