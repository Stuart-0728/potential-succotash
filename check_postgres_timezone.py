#!/usr/bin/env python3
import psycopg2
from datetime import datetime
import pytz

# 数据库连接信息
conn_params = {
    'dbname': 'cqnu_association_uxft',
    'user': 'cqnu_association_uxft_user',
    'password': 'BamPWSRTgj0sPGKM4sGsLDv8sGCPCPzB',
    'host': 'dpg-d0sjag49c44c73f7jt4g-a.oregon-postgres.render.com',
    'port': '5432'
}

try:
    # 连接到数据库
    print("正在连接到PostgreSQL数据库...")
    conn = psycopg2.connect(**conn_params)
    cursor = conn.cursor()
    
    # 检查数据库时区设置
    print("\n==== 检查数据库时区设置 ====")
    cursor.execute("SHOW timezone;")
    db_timezone = cursor.fetchone()[0]
    print(f"数据库时区: {db_timezone}")
    
    # 检查当前数据库时间
    cursor.execute("SELECT NOW();")
    db_time = cursor.fetchone()[0]
    print(f"数据库当前时间: {db_time}")
    
    # 获取本地时间（考虑时区）
    beijing_now = datetime.now(pytz.timezone('Asia/Shanghai'))
    print(f"本地北京时间: {beijing_now}")
    print(f"时间差异: {(beijing_now - db_time).total_seconds() / 3600:.2f} 小时")
    
    # 获取活动表结构
    print("\n==== 活动表结构 ====")
    cursor.execute("""
    SELECT column_name, data_type, is_nullable 
    FROM information_schema.columns 
    WHERE table_name = 'activities';
    """)
    columns = cursor.fetchall()
    for column in columns:
        print(f"{column[0]}: {column[1]} (可空: {column[2]})")
    
    # 检查活动时间
    print("\n==== 活动时间数据 ====")
    cursor.execute("""
    SELECT id, title, start_time, end_time, registration_deadline, created_at 
    FROM activities 
    ORDER BY created_at DESC 
    LIMIT 3;
    """)
    activities = cursor.fetchall()
    
    for activity in activities:
        id, title, start_time, end_time, reg_deadline, created_at = activity
        print(f"\n活动 ID: {id}, 标题: {title}")
        print(f"开始时间: {start_time} (时区信息: {start_time.tzinfo})")
        print(f"结束时间: {end_time} (时区信息: {end_time.tzinfo})")
        print(f"报名截止: {reg_deadline} (时区信息: {reg_deadline.tzinfo})")
        print(f"创建时间: {created_at} (时区信息: {created_at.tzinfo})")
        
        # 转换时间到北京时区显示
        if start_time.tzinfo:
            beijing_start = start_time.astimezone(pytz.timezone('Asia/Shanghai'))
        else:
            beijing_start = pytz.timezone('Asia/Shanghai').localize(start_time)
            
        print(f"北京时间显示: {beijing_start.strftime('%Y-%m-%d %H:%M:%S %Z%z')}")
    
    # 执行时区转换更新测试（不提交）
    print("\n==== 时区转换测试 ====")
    test_id = activities[0][0]
    
    # 读取原始值
    cursor.execute("SELECT start_time FROM activities WHERE id = %s", (test_id,))
    original_time = cursor.fetchone()[0]
    print(f"原始时间: {original_time}")
    
    # 测试时区转换SQL
    cursor.execute("""
    SELECT 
        start_time AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Shanghai' as beijing_time,
        start_time as original_time
    FROM activities 
    WHERE id = %s
    """, (test_id,))
    
    converted = cursor.fetchone()
    print(f"UTC->北京转换: {converted[0]}")
    print(f"原始时间: {converted[1]}")
    print(f"差异(小时): {(converted[0] - converted[1]).total_seconds() / 3600:.2f}")

finally:
    # 关闭连接
    if 'conn' in locals() and conn:
        conn.close()
        print("\n数据库连接已关闭") 