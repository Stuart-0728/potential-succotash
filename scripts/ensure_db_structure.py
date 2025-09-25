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

# ========== 新增：PostgreSQL 序列校正与自动恢复工具 ==========

def reset_postgres_sequences(app, db):
    """统一校正PostgreSQL中关键表的序列，避免主键冲突"""
    try:
        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        if not (db_uri and 'postgresql' in db_uri):
            return

        inspector = inspect(db.engine)
        existing_tables = set(inspector.get_table_names())

        # 仅针对存在的表进行处理，跳过无序列或非整数主键的表
        tables_with_pk_id = [
            ('roles', 'id'),
            ('users', 'id'),
            ('student_info', 'id'),
            ('tags', 'id'),
            ('activities', 'id'),
            ('registrations', 'id'),
            ('points_history', 'id'),
            ('activity_reviews', 'id'),
            ('announcements', 'id'),
            ('system_logs', 'id'),
            ('activity_checkins', 'id'),
            ('message', 'id'),
            ('notification', 'id'),
            ('notification_read', 'id'),
            ('ai_chat_history', 'id'),
        ]

        fixed = 0
        for table, pk in tables_with_pk_id:
            if table not in existing_tables:
                continue
            try:
                # 使用pg_get_serial_sequence自动解析序列名，兼容identity/serial
                sql = f"""
                    DO $$
                    DECLARE seq_name text;
                    BEGIN
                        SELECT pg_get_serial_sequence('public."{table}"','{pk}') INTO seq_name;
                        IF seq_name IS NOT NULL THEN
                            PERFORM setval(seq_name, GREATEST((SELECT COALESCE(MAX("{pk}"), 0) FROM public."{table}"), 0) + 1, false);
                        END IF;
                    END $$;
                """
                db.session.execute(text(sql))
                db.session.commit()
                fixed += 1
            except Exception as inner_e:
                logger.warning(f"校正序列失败 {table}.{pk}: {inner_e}")
                db.session.rollback()
        if fixed:
            logger.info(f"序列校正完成，已处理 {fixed} 张表")
        else:
            logger.info("无需要校正的序列或相关表不存在")
    except Exception as e:
        logger.warning(f"序列校正过程出现问题: {e}")
        try:
            db.session.rollback()
        except Exception:
            pass


def check_primary_minimal_state(app, db):
    """检测主库是否处于“最小/空”状态（仅基础管理员或无业务数据）"""
    try:
        inspector = inspect(db.engine)
        tables = set(inspector.get_table_names())

        # 若关键业务表都不存在，视为最小状态
        critical_tables = {'users', 'activities'}
        if not critical_tables.issubset(tables):
            logger.info("关键业务表缺失，判定为最小状态")
            return True

        # 活动数量为0即视为无业务数据
        try:
            activities_count = db.session.execute(text('SELECT COUNT(*) FROM "activities"')).scalar()
            if activities_count and activities_count > 0:
                logger.info(f"检测到 {activities_count} 条活动记录，非最小状态")
                return False
        except Exception as e:
            logger.warning(f"检测活动表失败: {e}")

        # 用户数小于等于2（通常为基础管理员）
        try:
            users_count = db.session.execute(text('SELECT COUNT(*) FROM "users"')).scalar()
            if users_count and users_count > 2:
                logger.info(f"检测到 {users_count} 个用户，非最小状态")
                return False
        except Exception as e:
            logger.warning(f"检测用户表失败: {e}")

        # 其他业务表存在数据也视为非最小
        more_tables = ['registrations', 'activity_checkins', 'points_history']
        for t in more_tables:
            if t in tables:
                try:
                    cnt = db.session.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar()
                    if cnt and cnt > 0:
                        logger.info(f"{t} 表存在 {cnt} 条记录，非最小状态")
                        return False
                except Exception:
                    pass

        logger.info("未检测到业务数据，判定为最小状态")
        return True
    except Exception as e:
        logger.warning(f"最小状态检测失败: {e}")
        return False


def auto_recover_primary(app, db):
    """在启动时执行健康检查与自动恢复：主库最小/空则从备库恢复并重置序列"""
    try:
        # 允许通过环境变量关闭
        if str(os.environ.get('AUTO_RECOVER_ON_START', 'true')).lower() not in ('1', 'true', 'yes', 'y'):  # 默认启用
            logger.info("已通过环境变量关闭启动自动恢复")
            return

        # 检查是否启用双库，及备库可用
        try:
            from src.dual_db_config import dual_db
            if not dual_db.is_dual_db_enabled():
                logger.info("双数据库未启用，跳过自动恢复")
                return
            info = dual_db.get_database_info()
            if not (info.get('primary') and info.get('backup')):
                logger.warning("主/备库连接异常，跳过自动恢复")
                return
        except Exception as e:
            logger.warning(f"双库状态检测失败，跳过自动恢复: {e}")
            return

        # 仅当主库最小状态时才尝试恢复
        if not check_primary_minimal_state(app, db):
            return

        logger.info("检测到主库为空或最小状态，开始从备库恢复（智能/完整）…")
        from src.db_sync import DatabaseSyncer
        syncer = DatabaseSyncer()

        # 强制完整恢复以快速建立业务数据
        recovered = syncer.safe_restore_from_clawcloud(force_full_restore=True)
        if recovered:
            logger.info("从备库恢复成功，开始重置序列…")
            reset_postgres_sequences(app, db)
            logger.info("自动恢复流程完成")
        else:
            logger.warning("从备库恢复失败，请检查备库数据与连接配置")
    except Exception as e:
        logger.warning(f"自动恢复流程出现异常: {e}")

# ========== 以上为新增工具函数 ==========

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
            
            # 针对PostgreSQL：统一校正所有关键表序列，防止主键冲突
            reset_postgres_sequences(app, db)
            
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
            
            # 启动时自动恢复（主库重置/为空时）
            try:
                auto_recover_primary(app, db)
            except Exception as e:
                logger.warning(f"启动自动恢复执行时出现问题: {e}")
            
            return True
        except Exception as e:
            logger.error(f"确保数据库结构时出错: {str(e)}")
            return False

if __name__ == "__main__":
    # 当直接运行此脚本时的代码
    print("此脚本设计为从应用程序导入，而不是直接运行")
    sys.exit(1)