#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试管理员访问权限
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.main import create_app
from src.models import db, User, Role

def test_admin_access():
    app = create_app()
    
    with app.app_context():
        # 查找管理员用户
        admin_role = db.session.execute(db.select(Role).filter_by(name='Admin')).scalar_one_or_none()
        if not admin_role:
            print("❌ 没有找到管理员角色")
            return
            
        admin_users = db.session.execute(db.select(User).filter_by(role_id=admin_role.id)).scalars().all()
        
        if not admin_users:
            print("❌ 没有找到管理员用户")
            return
            
        print("✅ 找到以下管理员用户:")
        for user in admin_users:
            print(f"   - 用户名: {user.username}")
            print(f"   - 邮箱: {user.email}")
            print(f"   - 激活状态: {user.active}")
            print(f"   - 角色: {user.role.name}")
            print()
            
        # 检查活动数据
        from src.models import Activity
        activities = db.session.execute(db.select(Activity)).scalars().all()
        print(f"✅ 数据库中有 {len(activities)} 个活动")
        
        if activities:
            print("前几个活动:")
            for activity in activities[:3]:
                print(f"   - ID: {activity.id}, 标题: {activity.title}, 签到状态: {getattr(activity, 'checkin_enabled', 'N/A')}")

if __name__ == '__main__':
    test_admin_access()