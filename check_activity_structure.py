#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
检查Activity表结构与模型定义的一致性
"""

import os
import sys
import logging
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_activity_table():
    """检查Activity表结构与模型定义的一致性"""
    try:
        # 导入应用
        from src import create_app, db
        from src.models import Activity
        
        # 创建Flask应用获取数据库上下文
        app = create_app()
        
        with app.app_context():
            # 检查数据库中的表
            inspector = sa_inspect(db.engine)
            db_tables = inspector.get_table_names()
            
            if 'activities' not in db_tables:
                logger.error("activities表不存在")
                return False
            
            # 获取表的列
            db_columns = {col['name']: col for col in inspector.get_columns('activities')}
            
            # 检查poster_image列是否存在
            if 'poster_image' not in db_columns:
                logger.error("activities表中不存在poster_image列")
                print("需要添加poster_image列到activities表")
                return False
            else:
                logger.info("activities表中存在poster_image列 ✓")
                print("活动海报功能已修复：activities表中存在poster_image列 ✓")
                return True
            
    except Exception as e:
        logger.error(f"检查Activity表时出错: {str(e)}")
        print(f"错误: {str(e)}")
        return False

if __name__ == '__main__':
    print(f"开始检查Activity表结构 - {datetime.now()}")
    if check_activity_table():
        print("检查完成，没有发现问题")
        sys.exit(0)
    else:
        print("检查完成，发现问题")
        sys.exit(1) 