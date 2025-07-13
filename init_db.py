#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""初始化数据库"""

import os
# 设置环境变量，确保使用production配置
os.environ['FLASK_CONFIG'] = 'production'

from src import create_app, db
from src.models import User, Role
from werkzeug.security import generate_password_hash

def init_database():
    """初始化数据库"""
    app = create_app('production')
    
    with app.app_context():
        # 创建所有表
        db.create_all()
        print("已创建所有数据库表")
        
        # 创建角色
        admin_role = db.session.query(Role).filter_by(name='Admin').first()
        if not admin_role:
            admin_role = Role(name='Admin', description='管理员')
            db.session.add(admin_role)
            db.session.commit()
            print("已创建管理员角色")
        
        # 创建管理员用户
        admin = db.session.query(User).filter_by(username='stuart').first()
        if admin:
            print(f"管理员用户已存在: {admin.username}")
        else:
            # 创建管理员用户
            admin = User(
                username='stuart',
                password_hash=generate_password_hash('LYXspassword123'),
                role_id=admin_role.id,
                active=True,
                email='admin@example.com'
            )
            
            # 添加到数据库
            db.session.add(admin)
            db.session.commit()
            
            print(f"管理员用户创建成功: {admin.username}")

if __name__ == "__main__":
    init_database() 