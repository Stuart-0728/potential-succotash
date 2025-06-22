#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
自动更新Render PostgreSQL数据库的脚本
用于执行数据库迁移和结构更新
"""

import os
import sys
import psycopg2
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_db_connection():
    """获取数据库连接"""
    try:
        # 从环境变量获取数据库连接信息
        host = os.environ.get('RENDER_POSTGRES_HOST')
        port = os.environ.get('RENDER_POSTGRES_PORT', '5432')
        user = os.environ.get('RENDER_POSTGRES_USER')
        password = os.environ.get('RENDER_POSTGRES_PASSWORD')
        dbname = os.environ.get('RENDER_POSTGRES_DB')
        
        # 验证必要的环境变量
        if not all([host, user, password, dbname]):
            logger.error("缺少必要的数据库连接环境变量")
            print("请设置以下环境变量:")
            print("- RENDER_POSTGRES_HOST: 数据库主机地址")
            print("- RENDER_POSTGRES_PORT: 数据库端口 (默认: 5432)")
            print("- RENDER_POSTGRES_USER: 数据库用户名")
            print("- RENDER_POSTGRES_PASSWORD: 数据库密码")
            print("- RENDER_POSTGRES_DB: 数据库名称")
            sys.exit(1)
        
        # 连接到数据库
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=dbname
        )
        
        logger.info(f"成功连接到数据库 {dbname} @ {host}")
        return conn
    
    except Exception as e:
        logger.error(f"连接数据库失败: {str(e)}")
        sys.exit(1)

def execute_sql_script(conn, script_path=None, sql_content=None):
    """执行SQL脚本"""
    try:
        cursor = conn.cursor()
        
        # 获取SQL内容
        if script_path and os.path.exists(script_path):
            with open(script_path, 'r') as f:
                sql = f.read()
        elif sql_content:
            sql = sql_content
        else:
            logger.error("未提供SQL脚本路径或内容")
            return False
        
        # 执行SQL
        cursor.execute(sql)
        conn.commit()
        
        logger.info("SQL脚本执行成功")
        return True
    
    except Exception as e:
        conn.rollback()
        logger.error(f"执行SQL脚本失败: {str(e)}")
        return False

def update_messaging_tables(conn):
    """更新消息和通知系统的表结构"""
    sql = """
    -- 检查是否存在旧的消息表，如果存在则删除
    DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'message') THEN
            DROP TABLE IF EXISTS notification_read;
            DROP TABLE IF EXISTS notification;
            DROP TABLE IF EXISTS message;
        END IF;
    END $$;

    -- 添加站内信表
    CREATE TABLE IF NOT EXISTS message (
        id SERIAL PRIMARY KEY,
        sender_id INTEGER NOT NULL,
        receiver_id INTEGER NOT NULL,
        subject VARCHAR(100) NOT NULL,
        content TEXT NOT NULL,
        is_read BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (sender_id) REFERENCES users(id),
        FOREIGN KEY (receiver_id) REFERENCES users(id)
    );

    -- 添加通知表
    CREATE TABLE IF NOT EXISTS notification (
        id SERIAL PRIMARY KEY,
        title VARCHAR(100) NOT NULL,
        content TEXT NOT NULL,
        is_important BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        created_by INTEGER NOT NULL,
        expiry_date TIMESTAMP WITH TIME ZONE,
        FOREIGN KEY (created_by) REFERENCES users(id)
    );

    -- 添加通知已读表
    CREATE TABLE IF NOT EXISTS notification_read (
        id SERIAL PRIMARY KEY,
        notification_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        read_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (notification_id) REFERENCES notification(id),
        FOREIGN KEY (user_id) REFERENCES users(id),
        UNIQUE (notification_id, user_id)
    );

    -- 创建相应的序列
    DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'message') THEN
            IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'message_id_seq') THEN
                CREATE SEQUENCE message_id_seq;
                ALTER TABLE message ALTER COLUMN id SET DEFAULT nextval('message_id_seq');
                SELECT setval('message_id_seq', COALESCE((SELECT MAX(id) FROM message), 0) + 1);
            END IF;
        END IF;

        IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'notification') THEN
            IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'notification_id_seq') THEN
                CREATE SEQUENCE notification_id_seq;
                ALTER TABLE notification ALTER COLUMN id SET DEFAULT nextval('notification_id_seq');
                SELECT setval('notification_id_seq', COALESCE((SELECT MAX(id) FROM notification), 0) + 1);
            END IF;
        END IF;

        IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'notification_read') THEN
            IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'notification_read_id_seq') THEN
                CREATE SEQUENCE notification_read_id_seq;
                ALTER TABLE notification_read ALTER COLUMN id SET DEFAULT nextval('notification_read_id_seq');
                SELECT setval('notification_read_id_seq', COALESCE((SELECT MAX(id) FROM notification_read), 0) + 1);
            END IF;
        END IF;
    END $$;
    """
    
    return execute_sql_script(conn, sql_content=sql)

def verify_tables(conn):
    """验证表结构是否正确"""
    try:
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name IN ('message', 'notification', 'notification_read')
        """)
        
        tables = [row[0] for row in cursor.fetchall()]
        
        if len(tables) == 3:
            logger.info("所有必要的表都已创建")
            
            # 检查外键约束
            cursor.execute("""
                SELECT
                    tc.table_name, 
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name 
                FROM 
                    information_schema.table_constraints AS tc 
                    JOIN information_schema.key_column_usage AS kcu
                      ON tc.constraint_name = kcu.constraint_name
                      AND tc.table_schema = kcu.table_schema
                    JOIN information_schema.constraint_column_usage AS ccu
                      ON ccu.constraint_name = tc.constraint_name
                      AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name IN ('message', 'notification', 'notification_read')
            """)
            
            constraints = cursor.fetchall()
            logger.info(f"找到 {len(constraints)} 个外键约束")
            
            for constraint in constraints:
                logger.info(f"表 {constraint[0]} 的 {constraint[1]} 列引用 {constraint[2]}.{constraint[3]}")
            
            return True
        else:
            logger.warning(f"缺少必要的表: 找到 {tables}，但需要 ['message', 'notification', 'notification_read']")
            return False
        
    except Exception as e:
        logger.error(f"验证表结构时出错: {str(e)}")
        return False

def main():
    """主函数"""
    logger.info("开始更新Render PostgreSQL数据库")
    
    # 连接数据库
    conn = get_db_connection()
    
    try:
        # 更新消息和通知系统的表结构
        if update_messaging_tables(conn):
            logger.info("消息和通知系统的表结构更新成功")
        else:
            logger.error("消息和通知系统的表结构更新失败")
        
        # 验证表结构
        if verify_tables(conn):
            logger.info("表结构验证通过")
        else:
            logger.warning("表结构验证未通过")
        
        logger.info("数据库更新完成")
    
    finally:
        # 关闭数据库连接
        conn.close()
        logger.info("数据库连接已关闭")

if __name__ == "__main__":
    main() 