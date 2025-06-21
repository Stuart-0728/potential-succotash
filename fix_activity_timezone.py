#!/usr/bin/env python3
"""
修复活动时间时区问题
将数据库中活动的时间统一为UTC存储格式
"""
import os
import sys
from datetime import datetime
import pytz
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from time import sleep

# 检查环境
is_render = os.environ.get('RENDER', False) or os.environ.get('IS_RENDER', False)
database_url = os.environ.get('DATABASE_URL')

if not database_url:
    # 本地SQLite数据库路径
    database_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'cqnu_association.db')
    database_url = f'sqlite:///{database_path}'
    db_type = 'sqlite'
else:
    # 替换PostgreSQL URL以符合SQLAlchemy要求
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://')
    db_type = 'postgresql'

try:
    # 创建数据库引擎
    engine = create_engine(database_url)
    
    print(f"连接到 {'Render PostgreSQL' if is_render else '本地SQLite'} 数据库...")
    
    with engine.connect() as conn:
        # 获取当前时区设置
        if db_type == 'postgresql':
            result = conn.execute(text("SHOW timezone;"))
            db_timezone = result.scalar()
            print(f"数据库时区: {db_timezone}")
            
            # 获取当前数据库时间
            result = conn.execute(text("SELECT NOW();"))
            db_time = result.scalar()
            print(f"数据库当前时间: {db_time}")
        else:
            print("SQLite不支持时区功能")
            
        # 获取本地时间
        local_now = datetime.now()
        print(f"本地时间: {local_now}")
        
        # 获取北京时间
        beijing_tz = pytz.timezone('Asia/Shanghai')
        beijing_now = datetime.now(beijing_tz)
        print(f"北京时间: {beijing_now}")
        
        # 如果运行在Render环境中
        if is_render:
            print("\n在Render环境中运行，需要将数据库中的时间调整到正确的UTC格式...")
            
            # 在PostgreSQL中直接查询活动表
            print("\n当前活动时间数据:")
            if db_type == 'postgresql':
                query_activities = text("""
                    SELECT id, title, start_time, end_time, registration_deadline 
                    FROM activities 
                    ORDER BY created_at DESC 
                    LIMIT 5;
                """)
                
                activities = conn.execute(query_activities).fetchall()
                
                for activity in activities:
                    print(f"ID: {activity.id}, 标题: {activity.title}")
                    print(f"  开始时间: {activity.start_time}")
                    print(f"  结束时间: {activity.end_time}")
                    print(f"  报名截止: {activity.registration_deadline}")
            
                print("\n正在修复时区问题...")
                input("按Enter键继续...")
                
                # 修复所有活动时间，将naive时间视为北京时间，并转换为UTC时间
                if db_type == 'postgresql':
                    # PostgreSQL环境下的修复
                    update_query = text("""
                        UPDATE activities 
                        SET 
                            start_time = (start_time AT TIME ZONE 'Asia/Shanghai') AT TIME ZONE 'UTC',
                            end_time = (end_time AT TIME ZONE 'Asia/Shanghai') AT TIME ZONE 'UTC',
                            registration_deadline = (registration_deadline AT TIME ZONE 'Asia/Shanghai') AT TIME ZONE 'UTC',
                            checkin_key_expires = CASE 
                                WHEN checkin_key_expires IS NOT NULL 
                                THEN (checkin_key_expires AT TIME ZONE 'Asia/Shanghai') AT TIME ZONE 'UTC'
                                ELSE checkin_key_expires
                            END
                    """)
                    
                    conn.execute(update_query)
                    conn.commit()
                    print("活动时间修复完成!")
                    
                    # 验证修复结果
                    print("\n修复后的活动时间数据:")
                    activities = conn.execute(query_activities).fetchall()
                    
                    for activity in activities:
                        print(f"ID: {activity.id}, 标题: {activity.title}")
                        print(f"  开始时间: {activity.start_time}")
                        print(f"  结束时间: {activity.end_time}")
                        print(f"  报名截止: {activity.registration_deadline}")
                else:
                    # SQLite环境暂不支持直接通过SQL进行时区转换
                    print("SQLite环境不支持直接通过SQL进行时区转换，请使用应用内功能修复")
        else:
            print("\n在本地环境运行，无需修改时区设置")
        
        print("\n处理完成!")

except SQLAlchemyError as e:
    print(f"数据库错误: {e}")
    sys.exit(1)
except Exception as e:
    print(f"发生错误: {e}")
    sys.exit(1) 