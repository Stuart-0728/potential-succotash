#!/usr/bin/env python
"""
确保数据库结构完整的脚本
在应用启动时自动运行，确保所有必要的表和列都存在
"""
import os
import sys
import logging
from sqlalchemy import inspect, text

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def ensure_db_structure(app, db):
    """确保数据库结构完整，包括所有必要的表和列"""
    with app.app_context():
        try:
            # 创建所有表
            db.create_all()
            logger.info("数据库表初始化完成")
            
            # 检查是否需要添加特定列
            inspector = inspect(db.engine)
            
            # 检查activities表的列
            if 'activities' in inspector.get_table_names():
                activities_columns = [col['name'] for col in inspector.get_columns('activities')]
                if 'checkin_enabled' not in activities_columns:
                    # SQLite不支持ALTER TABLE ADD COLUMN WITH DEFAULT值，所以我们需要特殊处理
                    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
                    if db_uri and 'sqlite' in db_uri:
                        # 对于SQLite，我们执行原始SQL
                        db.session.execute(text('ALTER TABLE activities ADD COLUMN checkin_enabled BOOLEAN DEFAULT FALSE'))
                        logger.info("已添加checkin_enabled列到activities表(SQLite)")
                    else:
                        # 对于PostgreSQL等其他数据库
                        db.session.execute(text('ALTER TABLE activities ADD COLUMN IF NOT EXISTS checkin_enabled BOOLEAN DEFAULT FALSE'))
                        logger.info("已添加checkin_enabled列到activities表(PostgreSQL)")
                    db.session.commit()
            
            return True
        except Exception as e:
            logger.error(f"确保数据库结构时出错: {str(e)}")
            return False

if __name__ == "__main__":
    # 当直接运行此脚本时的代码
    print("此脚本设计为从应用程序导入，而不是直接运行")
    sys.exit(1) 