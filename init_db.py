#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""初始化数据库"""

from src import create_app, db
from src.models import User
from werkzeug.security import generate_password_hash

def init_database():
    """初始化数据库"""
    app = create_app()
    
    with app.app_context():
        # 创建所有表
        db.create_all()
        print("已创建所有数据库表")
        
        # 创建管理员用户
        admin = db.session.execute(db.select(User).filter_by(username='stuart')).scalar_one_or_none()
        if admin:
            print(f"管理员用户已存在: {admin.username}")
        else:
            # 创建管理员用户
            admin = User(
                username='stuart',
                password_hash=generate_password_hash('LYXspassword123'),
                is_admin=True,
                is_active=True,
                real_name='管理员',
                student_id='admin',
                email='admin@example.com'
            )
            
            # 添加到数据库
            db.session.add(admin)
            db.session.commit()
            
            print(f"管理员用户创建成功: {admin.username}")

if __name__ == "__main__":
    init_database() 