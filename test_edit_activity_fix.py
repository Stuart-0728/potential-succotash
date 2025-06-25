#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from src import create_app
from src.models import db, Activity, Tag
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_activity_tags():
    """测试活动标签处理"""
    app = create_app()
    with app.app_context():
        try:
            # 获取所有活动
            activities = db.session.execute(db.select(Activity)).scalars().all()
            logger.info(f"数据库中的活动数量: {len(activities)}")
            for a in activities:
                logger.info(f"活动: ID={a.id}, 标题={a.title}")
            
            if not activities:
                logger.error("数据库中没有活动，无法进行测试")
                return
            
            # 使用第一个活动进行测试
            activity = activities[0]
            activity_id = activity.id
            logger.info(f"使用活动进行测试 - ID: {activity.id}, 标题: {activity.title}")
            
            # 打印当前标签
            current_tags = [tag.name for tag in activity.tags]
            logger.info(f"当前标签: {current_tags}")
            
            # 获取所有标签
            all_tags = db.session.execute(db.select(Tag)).scalars().all()
            logger.info(f"所有标签: {[(tag.id, tag.name) for tag in all_tags]}")
            
            # 测试清空标签
            logger.info("测试清空标签...")
            original_tags = list(activity.tags)
            activity.tags = []
            db.session.flush()
            logger.info(f"清空后的标签数量: {len(activity.tags)}")
            
            # 恢复原始标签
            logger.info("恢复原始标签...")
            activity.tags = original_tags
            db.session.flush()
            logger.info(f"恢复后的标签数量: {len(activity.tags)}")
            
            # 测试逐个添加标签
            logger.info("测试逐个添加标签...")
            activity.tags = []
            db.session.flush()
            
            # 选择前三个标签进行添加
            test_tags = all_tags[:3] if len(all_tags) >= 3 else all_tags
            for tag in test_tags:
                activity.tags.append(tag)
                logger.info(f"添加标签: {tag.name}")
            
            db.session.flush()
            logger.info(f"添加后的标签: {[tag.name for tag in activity.tags]}")
            
            # 回滚所有更改
            logger.info("回滚所有更改...")
            db.session.rollback()
            
            # 验证回滚后的标签
            activity = db.session.get(Activity, activity_id)
            if activity:
                final_tags = [tag.name for tag in activity.tags]
                logger.info(f"回滚后的标签: {final_tags}")
            else:
                logger.error(f"无法获取活动 ID={activity_id}")
            
            logger.info("测试完成")
            
        except Exception as e:
            logger.error(f"测试过程中出错: {e}", exc_info=True)
            db.session.rollback()

if __name__ == "__main__":
    test_activity_tags() 