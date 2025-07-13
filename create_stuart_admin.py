#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""创建指定的管理员用户"""

import os
import sys
import logging
from werkzeug.security import generate_password_hash

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 新的数据库URL
os.environ['DATABASE_URL'] = 'postgresql://cqnureg2_user:Pz8ZVfyLYOD22fkxp9w2XP7B9LsKAPqE@dpg-d1dugl7gi27c73er9p8g-a.oregon-postgres.render.com/cqnureg2'

def create_admin_user():
    """创建新的管理员用户"""
    try:
        # 导入应用程序
        from src import create_app, db
        from src.models import User, Role
        
        # 创建Flask应用获取数据库上下文
        app = create_app()
        
        with app.app_context():
            # 设置新管理员的用户名和密码
            username = 'stuart'
            password = 'LYXspassword123'
            email = 'stuart@example.com'
            
            print(f"正在创建管理员用户 '{username}'...")
            print(f"使用数据库: {app.config['SQLALCHEMY_DATABASE_URI']}")
            
            # 检查用户是否已存在
            stmt = db.select(User).filter_by(username=username)
            existing_user = db.session.execute(stmt).scalar_one_or_none()
            
            if existing_user:
                print(f"注意: 用户名 '{username}' 已存在，无需重新创建")
                return
            
            # 获取管理员角色
            admin_role_stmt = db.select(Role).filter_by(name='Admin')
            admin_role = db.session.execute(admin_role_stmt).scalar_one_or_none()
            
            if not admin_role:
                print("注意: 找不到管理员角色，正在创建...")
                admin_role = Role(name='Admin', description='管理员')
                db.session.add(admin_role)
                db.session.commit()
                print(f"管理员角色创建成功，ID: {admin_role.id}")
            
            # 创建新管理员用户
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
        import traceback
        traceback.print_exc()
        print(f"错误: {str(e)}")

if __name__ == '__main__':
    create_admin_user() 