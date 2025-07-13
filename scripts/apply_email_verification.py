#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
为用户表添加邮箱验证相关字段的脚本
"""

import os
import sys
import logging
from datetime import datetime
import pytz

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src import create_app, db
from src.models import User, Role

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def apply_migration():
    """应用邮箱验证字段迁移"""
    app = create_app('development')
    
    with app.app_context():
        try:
            # 检查数据库类型
            is_postgres = 'postgresql' in str(db.engine.url)
            
            # 读取SQL文件
            sql_file = 'scripts/add_email_verification.sql'
            with open(sql_file, 'r') as f:
                sql_content = f.read()
            
            # 根据数据库类型选择SQL语句
            if is_postgres:
                logger.info("检测到PostgreSQL数据库")
                # 使用PostgreSQL语法
                sql_statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip() and not stmt.strip().startswith('--') and not stmt.strip().startswith('-- SQLite')]
            else:
                logger.info("检测到SQLite数据库")
                # 使用SQLite语法
                sql_statements = []
                in_sqlite_block = False
                for line in sql_content.split('\n'):
                    if line.strip() == '-- SQLite版本':
                        in_sqlite_block = True
                        continue
                    if in_sqlite_block and line.strip() and not line.strip().startswith('--'):
                        sql_statements.append(line.strip())
            
            # 执行SQL语句
            conn = db.engine.connect()
            for stmt in sql_statements:
                if stmt:
                    logger.info(f"执行SQL: {stmt}")
                    try:
                        conn.execute(stmt)
                        conn.commit()
                    except Exception as e:
                        logger.error(f"执行SQL失败: {e}")
            
            # 关闭连接
            conn.close()
            
            # 设置管理员用户的邮箱已验证
            admin_role = db.session.query(Role).filter_by(name='Admin').first()
            if admin_role:
                admin_users = db.session.query(User).filter_by(role_id=admin_role.id).all()
                for user in admin_users:
                    user.email_confirmed = True
                    logger.info(f"设置管理员用户 {user.username} 的邮箱为已验证")
                db.session.commit()
            
            logger.info("邮箱验证字段迁移完成")
            
        except Exception as e:
            logger.error(f"迁移过程中发生错误: {e}")
            raise

if __name__ == '__main__':
    logger.info("开始应用邮箱验证字段迁移...")
    apply_migration()
    logger.info("邮箱验证字段迁移完成") 