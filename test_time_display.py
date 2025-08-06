#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试时间显示修复
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.models import db, Registration, Activity, User, StudentInfo
from src.utils.time_helpers import get_localized_now, display_datetime
from src import create_app
from datetime import datetime, timedelta
import pytz

def test_time_display():
    """测试时间显示修复"""
    app = create_app()
    
    with app.app_context():
        print("=== 时间显示修复测试 ===")
        
        # 获取当前时间
        current_utc = get_localized_now()
        print(f"当前UTC时间: {current_utc}")
        
        # 测试显示函数
        displayed_time = display_datetime(current_utc, 'Asia/Shanghai')
        print(f"显示的北京时间: {displayed_time}")
        
        # 计算预期的北京时间
        beijing_tz = pytz.timezone('Asia/Shanghai')
        utc_tz = pytz.UTC
        utc_aware = utc_tz.localize(current_utc)
        expected_beijing = utc_aware.astimezone(beijing_tz)
        print(f"预期的北京时间: {expected_beijing.strftime('%Y-%m-%d %H:%M')}")
        
        # 检查是否一致
        if displayed_time == expected_beijing.strftime('%Y-%m-%d %H:%M'):
            print("✅ 时间显示修复成功！")
        else:
            print("❌ 时间显示仍有问题")
            
        # 查找现有的签到记录进行测试
        registrations = db.session.execute(
            db.select(Registration)
            .filter(Registration.check_in_time.isnot(None))
            .limit(5)
        ).scalars().all()
        
        if registrations:
            print("\n=== 现有签到记录时间显示测试 ===")
            for reg in registrations:
                if reg.check_in_time:
                    displayed = display_datetime(reg.check_in_time, 'Asia/Shanghai')
                    print(f"签到记录ID {reg.id}: 存储时间={reg.check_in_time}, 显示时间={displayed}")
        else:
            print("\n没有找到现有的签到记录")
            
            # 创建一个测试签到记录
            activity = db.session.execute(db.select(Activity).limit(1)).scalar_one_or_none()
            user = db.session.execute(db.select(User).limit(1)).scalar_one_or_none()
            
            if activity and user:
                # 检查是否已有报名记录
                existing_reg = db.session.execute(
                    db.select(Registration).filter_by(
                        user_id=user.id,
                        activity_id=activity.id
                    )
                ).scalar_one_or_none()
                
                if not existing_reg:
                    # 创建报名记录
                    registration = Registration(
                        user_id=user.id,
                        activity_id=activity.id,
                        status='registered',
                        register_time=current_utc
                    )
                    db.session.add(registration)
                    db.session.commit()
                    existing_reg = registration
                
                # 更新签到时间
                existing_reg.check_in_time = current_utc
                existing_reg.status = 'attended'
                db.session.commit()
                
                displayed = display_datetime(existing_reg.check_in_time, 'Asia/Shanghai')
                print(f"\n=== 新创建的测试签到记录 ===")
                print(f"存储的UTC时间: {existing_reg.check_in_time}")
                print(f"显示的北京时间: {displayed}")
                
                # 验证时间差
                utc_aware = utc_tz.localize(existing_reg.check_in_time)
                beijing_time = utc_aware.astimezone(beijing_tz)
                expected_display = beijing_time.strftime('%Y-%m-%d %H:%M')
                
                if displayed == expected_display:
                    print("✅ 签到时间显示正确！")
                else:
                    print(f"❌ 签到时间显示错误，预期: {expected_display}")
            else:
                print("没有找到活动或用户数据进行测试")

if __name__ == '__main__':
    test_time_display()