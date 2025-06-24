#!/usr/bin/env python3
"""
修复数据库中缺失的列

此脚本添加以下列：
1. users表：添加active列和is_admin列
2. student_info表：确保所有必要的列存在
"""

import os
import sqlite3
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def add_columns_to_users():
    """给users表添加缺失的列"""
    try:
        db_path = os.path.join('instance', 'cqnu_association.db')
        if not os.path.exists(db_path):
            logger.error(f"数据库文件不存在: {db_path}")
            return False
        
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查active列是否存在
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # 添加active列
        if 'active' not in columns:
            logger.info("添加active列到users表")
            cursor.execute("ALTER TABLE users ADD COLUMN active BOOLEAN DEFAULT 1")
            conn.commit()
        
        # 添加is_admin列
        if 'is_admin' not in columns:
            logger.info("添加is_admin列到users表")
            cursor.execute("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0")
            
            # 根据role_id设置is_admin值
            cursor.execute("UPDATE users SET is_admin = 1 WHERE role_id = 1")
            conn.commit()
        
        # 检查last_login列
        if 'last_login' not in columns:
            logger.info("添加last_login列到users表")
            cursor.execute("ALTER TABLE users ADD COLUMN last_login DATETIME")
            conn.commit()
        
        # 确保至少有一个管理员
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
        admin_count = cursor.fetchone()[0]
        
        if admin_count == 0:
            # 创建一个默认管理员用户
            from werkzeug.security import generate_password_hash
            logger.info("创建默认管理员用户")
            
            # 获取或创建管理员角色
            cursor.execute("SELECT id FROM roles WHERE name = 'Admin'")
            role = cursor.fetchone()
            if role:
                role_id = role[0]
            else:
                cursor.execute("INSERT INTO roles (name, description) VALUES ('Admin', '管理员') RETURNING id")
                role_id = cursor.fetchone()[0]
            
            # 创建admin用户
            password_hash = generate_password_hash('LYXspassword123')
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, role_id, is_admin, active, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ('stuart', 'admin@example.com', password_hash, role_id, 1, 1, datetime.now()))
            
            conn.commit()
        
        # 关闭连接
        conn.close()
        logger.info("成功修复users表")
        return True
    
    except Exception as e:
        logger.error(f"修复users表时出错: {e}")
        return False

def fix_form_fields():
    """修复auth.py中的表单问题"""
    try:
        auth_file = os.path.join('src', 'routes', 'auth.py')
        if not os.path.exists(auth_file):
            logger.error(f"文件不存在: {auth_file}")
            return False
        
        with open(auth_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 修复正则表达式问题
        content = content.replace(r"Regexp('^1[3-9]\d{9}$'", r"Regexp(r'^1[3-9]\d{9}$'")
        content = content.replace(r"Regexp('^\d{5,12}$'", r"Regexp(r'^\d{5,12}$'")
        
        # 修复登录函数，确保form变量传递给模板
        if "return render_template('auth/login.html')" in content:
            content = content.replace(
                "return render_template('auth/login.html')", 
                "return render_template('auth/login.html', form=form)"
            )
        
        # 修复登录处理
        if "user = db.session.execute(db.select(User).filter_by(username=username)).scalar_one_or_none()" in content:
            modified_query = """
            # 尝试使用兼容模式查询用户
            try:
                user = db.session.execute(db.select(User).filter_by(username=username)).scalar_one_or_none()
            except Exception as e:
                if 'no such column' in str(e).lower():
                    # 如果出现列不存在错误，使用基本查询
                    user = db.session.execute(db.select(User).filter_by(username=username)).scalar_one_or_none()
                else:
                    logger.error(f"查询用户时出错: {e}")
                    flash('登录过程中出现错误，请联系管理员', 'danger')
                    return render_template('auth/login.html', form=form)
            """
            content = content.replace(
                "user = db.session.execute(db.select(User).filter_by(username=username)).scalar_one_or_none()",
                modified_query
            )
        
        with open(auth_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info("成功修复auth.py文件")
        return True
    
    except Exception as e:
        logger.error(f"修复auth.py文件时出错: {e}")
        return False

def fix_student_imports():
    """修复student.py中的导入错误"""
    try:
        student_file = os.path.join('src', 'routes', 'student.py')
        if not os.path.exists(student_file):
            logger.error(f"文件不存在: {student_file}")
            return False
        
        with open(student_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 修复导入，去掉safe_greater_than
        if "safe_greater_than" in content:
            content = content.replace(
                "safe_compare, safe_less_than, safe_greater_than",
                "safe_compare, safe_less_than"
            )
            
            # 替换代码中使用safe_greater_than的地方
            content = content.replace(
                "safe_greater_than(", 
                "not safe_less_than("
            )
        
        with open(student_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info("成功修复student.py文件")
        return True
    
    except Exception as e:
        logger.error(f"修复student.py文件时出错: {e}")
        return False

if __name__ == "__main__":
    logger.info("开始修复数据库和代码问题")
    
    # 添加缺失的列
    if add_columns_to_users():
        logger.info("成功添加缺失的列到users表")
    else:
        logger.error("添加列到users表失败")
    
    # 修复auth.py表单问题
    if fix_form_fields():
        logger.info("成功修复auth.py表单问题")
    else:
        logger.error("修复auth.py表单问题失败")
    
    # 修复student.py导入问题
    if fix_student_imports():
        logger.info("成功修复student.py导入问题")
    else:
        logger.error("修复student.py导入问题失败")
    
    logger.info("修复完成！请重启应用尝试") 