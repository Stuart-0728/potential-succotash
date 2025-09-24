#!/usr/bin/env python
"""
确保数据库结构完整的脚本
在应用启动时自动运行，确保所有必要的表和列都存在
"""
import os
import sys
import logging
import stat
from sqlalchemy import inspect, text

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def ensure_db_permissions(app):
    """确保数据库文件和目录有正确的权限"""
    try:
        db_path = app.config.get('DB_PATH')
        instance_path = app.config.get('INSTANCE_PATH')
        
        if not db_path or not instance_path:
            logger.warning("数据库路径未配置")
            return
        
        # 确保instance目录存在
        if not os.path.exists(instance_path):
            try:
                os.makedirs(instance_path, mode=0o777)
                logger.info(f"已创建数据库目录: {instance_path}")
            except Exception as e:
                logger.error(f"创建数据库目录失败: {e}")
        
        # 修改instance目录权限
        try:
            os.chmod(instance_path, 0o777)
            logger.info(f"已修改数据库目录权限为777: {instance_path}")
        except Exception as e:
            logger.error(f"修改数据库目录权限失败: {e}")
        
        # 修改数据库文件权限
        if os.path.exists(db_path):
            try:
                os.chmod(db_path, 0o666)
                logger.info(f"已修改数据库文件权限为666: {db_path}")
            except Exception as e:
                logger.error(f"修改数据库文件权限失败: {e}")
    except Exception as e:
        logger.error(f"设置数据库权限时出错: {e}")

def ensure_db_structure(app=None, db=None):
    """确保数据库结构完整，包括所有必要的表和列"""
    # 如果没有传递app和db，尝试自己导入
    if app is None or db is None:
        try:
            from flask import current_app
            from src.models import db as src_db
            app = current_app
            db = src_db
            logger.info("已自动导入app和db")
        except Exception as e:
            logger.error(f"无法自动导入app和db: {e}")
            return False
    
    with app.app_context():
        try:
            # 确保数据库文件和目录权限
            ensure_db_permissions(app)
            
            # 创建所有表
            db.create_all()
            logger.info("数据库表初始化完成")
            
            # 针对PostgreSQL：校正关键表的序列到当前最大ID，防止主键冲突
            try:
                db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
                if db_uri and 'postgresql' in db_uri:
                    logger.info("检测到PostgreSQL，开始校正关键表序列")
                    seq_fix_sql = [
                        # system_logs
                        text("SELECT setval('public.system_logs_id_seq', GREATEST((SELECT COALESCE(MAX(id), 0) FROM public.system_logs), 0)+1, false)")
                    ]
                    for stmt in seq_fix_sql:
                        try:
                            db.session.execute(stmt)
                            db.session.commit()
                        except Exception as inner_e:
                            logger.warning(f"尝试校正序列失败: {inner_e}")
                            db.session.rollback()
                    logger.info("序列校正完成")
            except Exception as e:
                logger.warning(f"序列校正过程出现问题: {e}")
                db.session.rollback()
            
            # 检查是否需要添加特定列
            inspector = inspect(db.engine)
            
            # 检查activities表的列
            if 'activities' in inspector.get_table_names():
                activities_columns = [col['name'] for col in inspector.get_columns('activities')]
                
                # 检查并添加checkin_enabled列
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
                
                # 检查并添加type列
                if 'type' not in activities_columns:
                    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
                    if db_uri and 'sqlite' in db_uri:
                        db.session.execute(text("ALTER TABLE activities ADD COLUMN type VARCHAR(50) DEFAULT '其他'"))
                        logger.info("已添加type列到activities表(SQLite)")
                    else:
                        db.session.execute(text("ALTER TABLE activities ADD COLUMN IF NOT EXISTS type VARCHAR(50) DEFAULT '其他'"))
                        logger.info("已添加type列到activities表(PostgreSQL)")
                    db.session.commit()
                
                # 检查并添加poster列
                if 'poster' not in activities_columns:
                    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
                    if db_uri and 'sqlite' in db_uri:
                        db.session.execute(text("ALTER TABLE activities ADD COLUMN poster VARCHAR(255)"))
                        logger.info("已添加poster列到activities表(SQLite)")
                    else:
                        db.session.execute(text("ALTER TABLE activities ADD COLUMN IF NOT EXISTS poster VARCHAR(255)"))
                        logger.info("已添加poster列到activities表(PostgreSQL)")
                    db.session.commit()
            
            # 检查users表的列
            if 'users' in inspector.get_table_names():
                users_columns = [col['name'] for col in inspector.get_columns('users')]
                
                # 检查并添加active列
                if 'active' not in users_columns:
                    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
                    if db_uri and 'sqlite' in db_uri:
                        db.session.execute(text('ALTER TABLE users ADD COLUMN active BOOLEAN DEFAULT TRUE'))
                        logger.info("已添加active列到users表(SQLite)")
                    else:
                        db.session.execute(text('ALTER TABLE users ADD COLUMN IF NOT EXISTS active BOOLEAN DEFAULT TRUE'))
                        logger.info("已添加active列到users表(PostgreSQL)")
                    db.session.commit()
                
                # 检查并添加last_login列
                if 'last_login' not in users_columns:
                    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
                    if db_uri and 'sqlite' in db_uri:
                        db.session.execute(text('ALTER TABLE users ADD COLUMN last_login TIMESTAMP'))
                        logger.info("已添加last_login列到users表(SQLite)")
                    else:
                        db.session.execute(text('ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP'))
                        logger.info("已添加last_login列到users表(PostgreSQL)")
                    db.session.commit()
            
            # 检查message表是否存在
            if 'message' not in inspector.get_table_names():
                # 创建message表
                logger.info("创建message表")
                db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
                if db_uri and 'sqlite' in db_uri:
                    db.session.execute(text('''
                    CREATE TABLE IF NOT EXISTS message (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        sender_id INTEGER NOT NULL,
                        receiver_id INTEGER NOT NULL,
                        subject VARCHAR(100) NOT NULL,
                        content TEXT NOT NULL,
                        is_read BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(sender_id) REFERENCES users(id),
                        FOREIGN KEY(receiver_id) REFERENCES users(id)
                    )
                    '''))
                else:
                    db.session.execute(text('''
                    CREATE TABLE IF NOT EXISTS message (
                        id SERIAL PRIMARY KEY,
                        sender_id INTEGER NOT NULL REFERENCES users(id),
                        receiver_id INTEGER NOT NULL REFERENCES users(id),
                        subject VARCHAR(100) NOT NULL,
                        content TEXT NOT NULL,
                        is_read BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    '''))
                db.session.commit()
                logger.info("message表创建成功")
            
            # 检查notification表是否存在
            if 'notification' not in inspector.get_table_names():
                # 创建notification表
                logger.info("创建notification表")
                db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
                if db_uri and 'sqlite' in db_uri:
                    db.session.execute(text('''
                    CREATE TABLE IF NOT EXISTS notification (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title VARCHAR(100) NOT NULL,
                        content TEXT NOT NULL,
                        is_important BOOLEAN DEFAULT FALSE,
                        is_public BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_by INTEGER NOT NULL,
                        expiry_date TIMESTAMP,
                        FOREIGN KEY(created_by) REFERENCES users(id)
                    )
                    '''))
                else:
                    db.session.execute(text('''
                    CREATE TABLE IF NOT EXISTS notification (
                        id SERIAL PRIMARY KEY,
                        title VARCHAR(100) NOT NULL,
                        content TEXT NOT NULL,
                        is_important BOOLEAN DEFAULT FALSE,
                        is_public BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_by INTEGER NOT NULL REFERENCES users(id),
                        expiry_date TIMESTAMP
                    )
                    '''))
                db.session.commit()
                logger.info("notification表创建成功")
            
            # 检查notification_read表是否存在
            if 'notification_read' not in inspector.get_table_names():
                # 创建notification_read表
                logger.info("创建notification_read表")
                db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
                if db_uri and 'sqlite' in db_uri:
                    db.session.execute(text('''
                    CREATE TABLE IF NOT EXISTS notification_read (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        notification_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        read_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(notification_id) REFERENCES notification(id),
                        FOREIGN KEY(user_id) REFERENCES users(id),
                        UNIQUE(notification_id, user_id)
                    )
                    '''))
                else:
                    db.session.execute(text('''
                    CREATE TABLE IF NOT EXISTS notification_read (
                        id SERIAL PRIMARY KEY,
                        notification_id INTEGER NOT NULL REFERENCES notification(id),
                        user_id INTEGER NOT NULL REFERENCES users(id),
                        read_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(notification_id, user_id)
                    )
                    '''))
                db.session.commit()
                logger.info("notification_read表创建成功")
            
            return True
        except Exception as e:
            logger.error(f"确保数据库结构时出错: {str(e)}")
            return False

if __name__ == "__main__":
    # 当直接运行此脚本时的代码
    print("此脚本设计为从应用程序导入，而不是直接运行")
    sys.exit(1)