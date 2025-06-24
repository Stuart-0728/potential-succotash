#!/usr/bin/env python3
"""
简单的测试消息创建脚本
直接使用SQLite连接，避免Flask-SQLAlchemy问题
"""

import os
import sys
import sqlite3
import logging
import traceback
from datetime import datetime

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_path():
    """获取数据库路径"""
    # 数据库文件路径
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'cqnu_association.db')

def execute_query(query, params=(), fetch=False):
    """执行SQL查询"""
    db_path = get_db_path()
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # 使用命名行
        cursor = conn.cursor()
        cursor.execute(query, params)
        
        result = None
        if fetch:
            result = cursor.fetchall()
        else:
            conn.commit()
        
        return result
    except Exception as e:
        logger.error(f"执行查询时出错: {e}")
        logger.error(traceback.format_exc())
        if conn:
            conn.rollback()
        return None
    finally:
        if conn:
            conn.close()

def check_db_structure():
    """检查数据库表结构"""
    # 检查message表结构
    table_info = execute_query("PRAGMA table_info(message)", fetch=True)
    
    if not table_info:
        logger.error("无法获取message表结构，可能表不存在")
        return False
    
    logger.info("=== Message表结构 ===")
    columns = []
    for col in table_info:
        col_dict = dict(col)
        columns.append(col_dict['name'])
        logger.info(f"列: {col_dict['name']}, 类型: {col_dict['type']}, 可空: {col_dict['notnull'] == 0}")
    
    logger.info(f"总共 {len(columns)} 列: {', '.join(columns)}")
    return True

def get_admin_and_student():
    """获取管理员和学生ID"""
    # 获取管理员角色ID
    admin_role = execute_query("SELECT id FROM roles WHERE name = 'Admin'", fetch=True)
    if not admin_role:
        logger.error("未找到管理员角色")
        return None, None
    
    admin_role_id = admin_role[0]['id']
    logger.info(f"管理员角色ID: {admin_role_id}")
    
    # 获取学生角色ID
    student_role = execute_query("SELECT id FROM roles WHERE name = 'Student'", fetch=True)
    if not student_role:
        logger.error("未找到学生角色")
        return None, None
    
    student_role_id = student_role[0]['id']
    logger.info(f"学生角色ID: {student_role_id}")
    
    # 获取一个管理员用户
    admin = execute_query("SELECT id, username FROM users WHERE role_id = ?", (admin_role_id,), fetch=True)
    if not admin or len(admin) == 0:
        logger.error("未找到管理员用户")
        return None, None
    
    admin_id = admin[0]['id']
    admin_username = admin[0]['username']
    logger.info(f"管理员用户: {admin_username} (ID: {admin_id})")
    
    # 获取一个学生用户
    student = execute_query("SELECT id, username FROM users WHERE role_id = ?", (student_role_id,), fetch=True)
    if not student or len(student) == 0:
        logger.error("未找到学生用户")
        return None, None
    
    student_id = student[0]['id']
    student_username = student[0]['username']
    logger.info(f"学生用户: {student_username} (ID: {student_id})")
    
    return admin_id, student_id

def create_test_message(sender_id, receiver_id):
    """创建测试消息"""
    if not sender_id or not receiver_id:
        logger.error("发送者或接收者ID无效")
        return False
    
    try:
        now = datetime.now()
        subject = f"测试消息 - {now.strftime('%Y-%m-%d %H:%M:%S')}"
        content = f"这是一条测试消息，用于验证站内信系统是否正常工作。\n\n发送时间: {now.strftime('%Y-%m-%d %H:%M:%S')}"
        is_read = 0  # 未读状态
        
        # 获取表结构，决定是否需要传递其他字段
        columns_query = execute_query("PRAGMA table_info(message)", fetch=True)
        columns = [col['name'] for col in columns_query]
        
        query = "INSERT INTO message (sender_id, receiver_id, subject, content, is_read, created_at) VALUES (?, ?, ?, ?, ?, ?)"
        params = (sender_id, receiver_id, subject, content, is_read, now.strftime('%Y-%m-%d %H:%M:%S'))
        
        # 执行插入，打印详细日志
        logger.info(f"执行SQL: {query}")
        logger.info(f"参数: {params}")
        
        db_path = get_db_path()
        conn = None
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            logger.info(f"成功创建测试消息: {subject}")
            return True
        except sqlite3.Error as e:
            logger.error(f"SQLite错误: {e}")
            logger.error(traceback.format_exc())
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()
    except Exception as e:
        logger.error(f"创建消息时出错: {e}")
        logger.error(traceback.format_exc())
        return False

def check_message_count():
    """检查消息总数"""
    result = execute_query("SELECT COUNT(*) as count FROM message", fetch=True)
    if result:
        count = result[0]['count']
        logger.info(f"站内信总数: {count}条")
        return count
    return 0

def list_tables():
    """列出数据库中的所有表"""
    tables = execute_query("SELECT name FROM sqlite_master WHERE type='table'", fetch=True)
    if tables:
        logger.info("=== 数据库表 ===")
        for table in tables:
            logger.info(f"表: {table['name']}")
    else:
        logger.error("无法获取数据库表")

def main():
    """主函数"""
    logger.info("==== 创建测试站内信 ====")
    
    # 检查数据库是否存在
    db_path = get_db_path()
    if not os.path.exists(db_path):
        logger.error(f"数据库文件不存在: {db_path}")
        return False
    
    logger.info(f"使用数据库: {db_path}")
    
    # 列出所有表
    list_tables()
    
    # 检查数据库结构
    if not check_db_structure():
        logger.error("数据库结构检查失败")
        return False
    
    # 检查当前消息数量
    initial_count = check_message_count()
    
    # 获取管理员和学生
    admin_id, student_id = get_admin_and_student()
    if not admin_id or not student_id:
        return False
    
    # 创建测试消息
    logger.info(f"从管理员(ID:{admin_id})向学生(ID:{student_id})发送测试消息")
    success = create_test_message(admin_id, student_id)
    
    if success:
        # 再次检查消息数量
        final_count = check_message_count()
        if final_count > initial_count:
            logger.info(f"消息数量增加: {initial_count} -> {final_count}")
            logger.info("测试消息创建成功!")
        else:
            logger.warning("消息数量未增加，可能创建失败")
    
    logger.info("==== 测试完成 ====")
    logger.info("请登录学生账号查看是否能收到新消息")
    
    return success

if __name__ == "__main__":
    main() 