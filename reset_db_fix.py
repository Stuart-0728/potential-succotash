#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
重置数据库并初始化基本数据
"""

import os
import shutil
import json
import sqlite3
import logging
import datetime
import subprocess
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 数据库路径
DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
DB_PATH = os.path.join(DB_DIR, 'cqnu_association.db')
BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src', 'backups')

def backup_database():
    """备份现有数据库"""
    # 确保备份目录存在
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR, mode=0o755)
    
    # 创建备份文件名
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(BACKUP_DIR, f'db_backup_{timestamp}.db')
    
    # 如果数据库存在则备份
    if os.path.exists(DB_PATH):
        try:
            shutil.copy2(DB_PATH, backup_path)
            logger.info(f"数据库已备份到: {backup_path}")
            # 设置备份文件的权限
            os.chmod(backup_path, 0o644)
            return True
        except Exception as e:
            logger.error(f"数据库备份失败: {e}")
            return False
    else:
        logger.warning("数据库文件不存在，无需备份")
        return True

def reset_database():
    """重置数据库"""
    # 删除现有数据库
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            logger.info("已删除现有数据库")
        except Exception as e:
            logger.error(f"删除数据库失败: {e}")
            return False
    
    # 确保实例目录存在并有正确权限
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR, mode=0o755)
    else:
        os.chmod(DB_DIR, 0o755)
    
    # 创建新数据库
    try:
        # 创建数据库文件
        conn = sqlite3.connect(DB_PATH)
        conn.close()
        
        # 设置数据库文件权限
        os.chmod(DB_PATH, 0o644)
        logger.info(f"已创建新数据库文件并设置权限: {DB_PATH}")
        
        # 使用SQL脚本初始化数据库结构
        init_script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts', 'reset_sqlite_db.sql')
        if os.path.exists(init_script_path):
            with open(init_script_path, 'r') as f:
                sql_script = f.read()
            
            conn = sqlite3.connect(DB_PATH)
            conn.executescript(sql_script)
            conn.commit()
            conn.close()
            logger.info("已使用SQL脚本初始化数据库结构")
        else:
            logger.warning("未找到SQL初始化脚本，将依赖Flask-SQLAlchemy创建表")
        
        return True
    except Exception as e:
        logger.error(f"创建数据库失败: {e}")
        return False

def create_admin_user():
    """创建管理员用户"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 检查用户表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            logger.warning("users表不存在，跳过创建管理员")
            conn.close()
            return False
        
        # 检查管理员是否已存在
        cursor.execute("SELECT id FROM users WHERE username = 'stuart'")
        if cursor.fetchone():
            logger.info("管理员用户已存在")
            conn.close()
            return True
        
        # 创建管理员用户
        # 密码: LYXspassword123 (使用Werkzeug的generate_password_hash生成的哈希)
        password_hash = 'pbkdf2:sha256:260000$VTv1hYZQEXvjjVFJ$a7fa5c066d08d1b41c001f5e3be18ba7b2c9ec9cb7f3a422abda7f9ae5aa4d46'
        
        cursor.execute("""
        INSERT INTO users (username, password_hash, email, is_admin, is_active, real_name, student_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ('stuart', password_hash, 'admin@example.com', 1, 1, '管理员', 'admin', datetime.datetime.utcnow()))
        
        conn.commit()
        conn.close()
        
        logger.info("已创建管理员用户")
        return True
    except Exception as e:
        logger.error(f"创建管理员用户失败: {e}")
        return False

def check_db_permissions():
    """检查数据库文件权限"""
    try:
        # 检查实例目录权限
        dir_stat = os.stat(DB_DIR)
        dir_perms = oct(dir_stat.st_mode)[-3:]
        logger.info(f"实例目录权限: {dir_perms}")
        
        # 如果目录权限不是755，修正它
        if dir_perms != '755':
            os.chmod(DB_DIR, 0o755)
            logger.info("已修正实例目录权限为755")
        
        # 检查数据库文件权限
        if os.path.exists(DB_PATH):
            file_stat = os.stat(DB_PATH)
            file_perms = oct(file_stat.st_mode)[-3:]
            logger.info(f"数据库文件权限: {file_perms}")
            
            # 如果文件权限不是644，修正它
            if file_perms != '644':
                os.chmod(DB_PATH, 0o644)
                logger.info("已修正数据库文件权限为644")
        
        return True
    except Exception as e:
        logger.error(f"检查权限失败: {e}")
        return False

def fix_permissions_with_sudo():
    """使用sudo修复权限"""
    try:
        # 使用sudo修复实例目录权限
        subprocess.run(['sudo', 'chmod', '755', DB_DIR], check=True)
        logger.info("已使用sudo修复实例目录权限")
        
        # 使用sudo修复数据库文件权限
        if os.path.exists(DB_PATH):
            subprocess.run(['sudo', 'chmod', '644', DB_PATH], check=True)
            logger.info("已使用sudo修复数据库文件权限")
        
        return True
    except Exception as e:
        logger.error(f"使用sudo修复权限失败: {e}")
        return False

def main():
    """主函数"""
    logger.info("开始重置数据库...")
    
    # 备份现有数据库
    if not backup_database():
        logger.error("数据库备份失败，终止重置过程")
        return False
    
    # 重置数据库
    if not reset_database():
        logger.error("数据库重置失败")
        return False
    
    # 检查和修复权限
    if not check_db_permissions():
        logger.warning("普通权限检查失败，尝试使用sudo修复")
        if not fix_permissions_with_sudo():
            logger.error("权限修复失败，可能需要手动修复")
    
    # 创建管理员用户
    if not create_admin_user():
        logger.warning("创建管理员用户失败，可能需要使用Flask shell创建")
    
    logger.info("数据库重置完成")
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("数据库重置成功！")
    else:
        print("数据库重置过程中出现错误，请查看日志。") 