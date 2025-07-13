import os
import sys
from datetime import datetime, timedelta
import logging
from flask import Flask
from src import create_app
from src.models import db, Activity, User, Tag
from src.utils.time_helpers import normalize_datetime_for_db, display_datetime, get_beijing_time

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 创建Flask应用
app = create_app()
# 确保SQLAlchemy实例与应用关联
with app.app_context():
    db.init_app(app)

def create_test_activity():
    """创建测试活动以验证时区修复"""
    with app.app_context():
        try:
            # 获取管理员用户
            admin = db.session.execute(db.select(User).filter_by(username='admin')).scalar_one_or_none()
            if not admin:
                logger.error("未找到管理员用户，无法创建活动")
                return False
            
            # 获取当前北京时间
            now = get_beijing_time()
            logger.info(f"当前北京时间: {now}")
            
            # 创建活动
            activity = Activity(
                title="时区测试活动",
                description="这是一个用于测试时区修复的活动",
                location="线上测试",
                start_time=normalize_datetime_for_db(now + timedelta(hours=1)),
                end_time=normalize_datetime_for_db(now + timedelta(hours=3)),
                registration_deadline=normalize_datetime_for_db(now + timedelta(minutes=30)),
                max_participants=50,
                status='active',
                is_featured=True,
                points=20,
                created_by=admin.id
            )
            
            # 保存到数据库
            db.session.add(activity)
            db.session.commit()
            
            # 打印活动时间信息
            logger.info(f"活动ID: {activity.id}")
            logger.info(f"数据库中的开始时间(UTC无时区): {activity.start_time}")
            logger.info(f"开始时间显示(北京时间): {display_datetime(activity.start_time)}")
            logger.info(f"数据库中的结束时间(UTC无时区): {activity.end_time}")
            logger.info(f"结束时间显示(北京时间): {display_datetime(activity.end_time)}")
            
            return True
        except Exception as e:
            logger.error(f"创建测试活动失败: {e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    logger.info("开始创建测试活动...")
    result = create_test_activity()
    if result:
        logger.info("测试活动创建成功")
    else:
        logger.error("测试活动创建失败") 