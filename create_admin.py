#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""创建管理员用户"""

import os
import sys
import logging
from werkzeug.security import generate_password_hash

# Add the project root directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_admin_user():
    """创建新的管理员用户"""
    try:
        # Import from the application
        from src import create_app, db
        from src.models import User, Role
        
        # Create a Flask app to get the database context
        app = create_app()
        
        with app.app_context():
            # Specify the username and password for the new admin
            username = 'stuart'
            password = 'LYXspassword123'
            email = 'stuart@example.com'
            
            print(f"正在创建管理员用户 '{username}'...")
            
            # Check if the user already exists
            stmt = db.select(User).filter_by(username=username)
            existing_user = db.session.execute(stmt).scalar_one_or_none()
            
            if existing_user:
                print(f"错误: 用户名 '{username}' 已存在")
                return
            
            # Get the admin role
            admin_role_stmt = db.select(Role).filter_by(name='Admin')
            admin_role = db.session.execute(admin_role_stmt).scalar_one_or_none()
            
            if not admin_role:
                print("错误: 找不到管理员角色，正在创建...")
                admin_role = Role(name='Admin', description='管理员')
                db.session.add(admin_role)
                db.session.commit()
            
            # Create the new admin user
            new_admin = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
                role_id=admin_role.id,
                active=True
            )
            
            db.session.add(new_admin)
            db.session.commit()
            
            logger.info(f"管理员用户 '{username}' 创建成功")
            print(f"成功! 管理员用户 '{username}' 已创建")
            print(f"  用户名: {username}")
            print(f"  密码: {password}")
            print(f"  邮箱: {email}")
            print("请使用这些凭据登录系统。")
        
    except Exception as e:
        logger.error(f"创建管理员用户出错: {str(e)}")
        print(f"错误: {str(e)}")
        print("请确保你已经激活了虚拟环境，并且数据库配置正确。")

if __name__ == '__main__':
    create_admin_user() 