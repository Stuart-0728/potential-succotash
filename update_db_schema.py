#!/usr/bin/env python
"""
更新数据库架构，添加completed_at字段到activities表
"""

import os
import sys
from datetime import datetime
import pytz

# 设置环境变量
os.environ['FLASK_APP'] = 'src'

# 导入应用和数据库
from src import create_app, db
from sqlalchemy import text

def update_schema():
    """更新数据库架构，添加completed_at字段到activities表"""
    app = create_app()
    with app.app_context():
        try:
            # 检查字段是否已存在
            result = db.session.execute(text(
                "SELECT COUNT(*) FROM information_schema.columns "
                "WHERE table_name = 'activities' AND column_name = 'completed_at'"
            )).scalar()
            
            if result > 0:
                print("字段 'completed_at' 已存在于 'activities' 表中")
                return
            
            # 添加字段
            db.session.execute(text('ALTER TABLE activities ADD COLUMN completed_at TIMESTAMP WITH TIME ZONE'))
            
            # 更新已完成活动的completed_at字段
            db.session.execute(text(
                "UPDATE activities SET completed_at = NOW() "
                "WHERE status = 'completed' AND completed_at IS NULL"
            ))
            
            db.session.commit()
            print("成功添加 completed_at 字段到 activities 表")
            
        except Exception as e:
            db.session.rollback()
            print(f"更新数据库架构时出错: {e}")
            
            # 尝试SQLite语法
            try:
                db.session.execute(text('ALTER TABLE activities ADD COLUMN completed_at DATETIME'))
                db.session.commit()
                print("成功添加 completed_at 字段到 activities 表 (SQLite)")
            except Exception as e2:
                db.session.rollback()
                print(f"使用SQLite语法更新数据库架构时出错: {e2}")
                sys.exit(1)

if __name__ == '__main__':
    update_schema() 