#!/usr/bin/env python
"""
此脚本用于为数据库users表添加缺失的active和last_login列
"""
import os
import sys
import logging
from sqlalchemy import create_engine, text, inspect
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 数据库路径
INSTANCE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
DB_PATH = os.path.join(INSTANCE_PATH, 'cqnu_association.db')

def ensure_db_permissions():
    """确保数据库文件和目录有正确的权限"""
    try:
        # 确保instance目录存在
        if not os.path.exists(INSTANCE_PATH):
            try:
                os.makedirs(INSTANCE_PATH, mode=0o777)
                print(f"已创建数据库目录: {INSTANCE_PATH}")
            except Exception as e:
                print(f"创建数据库目录失败: {e}")
        
        # 修改instance目录权限
        try:
            os.chmod(INSTANCE_PATH, 0o777)
            print(f"已修改数据库目录权限为777: {INSTANCE_PATH}")
        except Exception as e:
            print(f"修改数据库目录权限失败: {e}")
        
        # 修改数据库文件权限
        if os.path.exists(DB_PATH):
            try:
                os.chmod(DB_PATH, 0o666)
                print(f"已修改数据库文件权限为666: {DB_PATH}")
            except Exception as e:
                print(f"修改数据库文件权限失败: {e}")
    except Exception as e:
        print(f"设置数据库权限时出错: {e}")

def add_missing_columns():
    """添加缺失的users表列"""
    try:
        # 确保数据库权限正确
        ensure_db_permissions()
        
        # 创建数据库连接
        engine = create_engine(f'sqlite:///{DB_PATH}')
        
        # 检查表和列
        inspector = inspect(engine)
        
        # 检查users表的列
        if 'users' in inspector.get_table_names():
            users_columns = [col['name'] for col in inspector.get_columns('users')]
            
            # 检查并添加active列
            if 'active' not in users_columns:
                with engine.connect() as conn:
                    conn.execute(text('ALTER TABLE users ADD COLUMN active BOOLEAN DEFAULT TRUE'))
                    print("已添加active列到users表")
            
            # 检查并添加last_login列
            if 'last_login' not in users_columns:
                with engine.connect() as conn:
                    conn.execute(text('ALTER TABLE users ADD COLUMN last_login TIMESTAMP'))
                    print("已添加last_login列到users表")
        
        # 检查activities表的列
        if 'activities' in inspector.get_table_names():
            activities_columns = [col['name'] for col in inspector.get_columns('activities')]
            
            # 检查并添加type列
            if 'type' not in activities_columns:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE activities ADD COLUMN type VARCHAR(50) DEFAULT '其他'"))
                    print("已添加type列到activities表")
            
            # 检查并添加checkin_enabled列
            if 'checkin_enabled' not in activities_columns:
                with engine.connect() as conn:
                    conn.execute(text('ALTER TABLE activities ADD COLUMN checkin_enabled BOOLEAN DEFAULT FALSE'))
                    print("已添加checkin_enabled列到activities表")
        
        print("数据库结构更新完成")
        return True
        
    except Exception as e:
        print(f"添加缺失列时出错: {e}")
        return False

if __name__ == "__main__":
    print("开始检查和添加缺失的数据库列...")
    if add_missing_columns():
        print("成功完成！")
    else:
        print("操作失败，请检查日志")
        sys.exit(1) 