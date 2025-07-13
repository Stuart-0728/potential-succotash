#!/usr/bin/env python
"""
更新远程PostgreSQL数据库架构，添加completed_at字段到activities表
"""

import os
import sys
import psycopg2
from datetime import datetime

# 数据库连接信息
DB_URL = "postgresql://cqnureg2_user:Pz8ZVfyLYOD22fkxp9w2XP7B9LsKAPqE@dpg-d1dugl7gi27c73er9p8g-a.oregon-postgres.render.com/cqnureg2"

def update_schema():
    """更新数据库架构，添加completed_at字段到activities表"""
    conn = None
    try:
        # 连接到数据库
        print("正在连接到远程PostgreSQL数据库...")
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        
        # 检查字段是否已存在
        print("检查字段是否已存在...")
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_name = 'activities' AND column_name = 'completed_at'"
        )
        result = cursor.fetchone()
        
        if result and result[0] > 0:
            print("字段 'completed_at' 已存在于 'activities' 表中")
            conn.close()
            return
        
        # 添加字段
        print("添加 completed_at 字段...")
        cursor.execute('ALTER TABLE activities ADD COLUMN completed_at TIMESTAMP WITH TIME ZONE')
        
        # 更新已完成活动的completed_at字段
        print("更新已完成活动的completed_at字段...")
        cursor.execute(
            "UPDATE activities SET completed_at = NOW() "
            "WHERE status = 'completed' AND completed_at IS NULL"
        )
        
        # 提交更改
        conn.commit()
        print("成功添加 completed_at 字段到 activities 表")
        
    except Exception as e:
        print(f"更新数据库架构时出错: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    update_schema() 