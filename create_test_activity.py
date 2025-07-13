from src import create_app
from src.models import db, Activity
from datetime import datetime, timedelta

app = create_app()

with app.app_context():
    now = datetime.now()
    
    # 创建一个当前时间可以签到的活动
    activity = Activity(
        title='测试签到活动',
        description='用于测试签到功能',
        location='线上',
        start_time=now - timedelta(hours=1),  # 开始时间为1小时前
        end_time=now + timedelta(hours=1),    # 结束时间为1小时后
        registration_deadline=now - timedelta(minutes=30),
        status='active',
        max_participants=100,
        created_by=1
    )
    
    db.session.add(activity)
    db.session.commit()
    
    print(f'创建测试活动成功，ID: {activity.id}')
    print(f'开始时间: {activity.start_time}')
    print(f'结束时间: {activity.end_time}')
    print(f'当前时间: {now}') 