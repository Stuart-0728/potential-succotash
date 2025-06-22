#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
修复活动时间的时区问题
此脚本用于批量修复数据库中已有活动的时间
将所有时间转换为UTC时间（无时区信息）
"""

import os
import sys
import pytz
from datetime import datetime
from sqlalchemy import create_engine, MetaData, Table, select, update
from sqlalchemy.orm import sessionmaker

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.utils.time_helpers import normalize_datetime_for_db, ensure_timezone_aware

def fix_activity_timezone(db_uri):
    """修复活动时间的时区问题"""
    print("开始修复活动时间的时区问题...")
    
    # 连接数据库
    engine = create_engine(db_uri)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # 获取活动表
        metadata = MetaData()
        metadata.reflect(bind=engine)
        activity_table = metadata.tables['activity']
        
        # 查询所有活动
        activities = session.execute(select(activity_table)).fetchall()
        
        count = 0
        for activity in activities:
            # 获取需要修复的时间字段
            start_time = activity.start_time
            end_time = activity.end_time
            registration_deadline = activity.registration_deadline
            
            # 修复时间字段
            fixed_start_time = normalize_datetime_for_db(ensure_timezone_aware(start_time))
            fixed_end_time = normalize_datetime_for_db(ensure_timezone_aware(end_time))
            fixed_registration_deadline = normalize_datetime_for_db(ensure_timezone_aware(registration_deadline))
            
            # 更新数据库
            stmt = update(activity_table).where(
                activity_table.c.id == activity.id
            ).values(
                start_time=fixed_start_time,
                end_time=fixed_end_time,
                registration_deadline=fixed_registration_deadline
            )
            session.execute(stmt)
            count += 1
        
        # 提交更改
        session.commit()
        print(f"成功修复 {count} 个活动的时间字段")
        
    except Exception as e:
        session.rollback()
        print(f"修复过程中发生错误: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    # 获取数据库URI
    if os.environ.get('RENDER', '') == 'true':
        # Render环境使用PostgreSQL
        db_uri = os.environ.get('DATABASE_URL')
        if db_uri and db_uri.startswith('postgres://'):
            db_uri = db_uri.replace('postgres://', 'postgresql://', 1)
    else:
        # 本地环境使用SQLite
        db_uri = 'sqlite:///instance/cqnu_association.db'
    
    fix_activity_timezone(db_uri) 