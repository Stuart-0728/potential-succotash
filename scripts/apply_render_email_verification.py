#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
为 Render 上的 PostgreSQL 数据库添加邮箱验证相关字段的脚本
"""

import os
import sys
import logging
import psycopg2
from psycopg2 import sql

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Render PostgreSQL 数据库连接信息
DB_URL = "postgresql://cqnureg2_user:Pz8ZVfyLYOD22fkxp9w2XP7B9LsKAPqE@dpg-d1dugl7gi27c73er9p8g-a.oregon-postgres.render.com/cqnureg2"

def apply_migration():
    """应用邮箱验证字段迁移到 Render 的 PostgreSQL 数据库"""
    try:
        # 连接到数据库
        logger.info("正在连接到 Render PostgreSQL 数据库...")
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        
        # 执行 SQL 语句
        logger.info("开始执行数据库迁移...")
        
        # 1. 添加 email_confirmed 字段
        logger.info("添加 email_confirmed 字段...")
        cursor.execute("""
        ALTER TABLE users ADD COLUMN IF NOT EXISTS email_confirmed BOOLEAN DEFAULT FALSE;
        """)
        
        # 2. 添加 confirmation_token 字段
        logger.info("添加 confirmation_token 字段...")
        cursor.execute("""
        ALTER TABLE users ADD COLUMN IF NOT EXISTS confirmation_token VARCHAR(128);
        """)
        
        # 3. 添加 confirmation_token_expires 字段
        logger.info("添加 confirmation_token_expires 字段...")
        cursor.execute("""
        ALTER TABLE users ADD COLUMN IF NOT EXISTS confirmation_token_expires TIMESTAMP WITH TIME ZONE;
        """)
        
        # 4. 为管理员用户自动设置邮箱已验证
        logger.info("设置管理员用户的邮箱为已验证...")
        cursor.execute("""
        UPDATE users
        SET email_confirmed = TRUE
        WHERE id IN (
            SELECT u.id 
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE r.name = 'Admin'
        );
        """)
        
        # 5. 添加索引以提高查询性能
        logger.info("添加索引...")
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_users_email_confirmed ON users (email_confirmed);
        """)
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_users_confirmation_token ON users (confirmation_token);
        """)
        
        # 提交更改
        conn.commit()
        logger.info("数据库迁移成功完成！")
        
        # 关闭连接
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"迁移过程中发生错误: {e}")
        raise

if __name__ == '__main__':
    logger.info("开始应用邮箱验证字段迁移到 Render 数据库...")
    apply_migration()
    logger.info("邮箱验证字段迁移完成") 