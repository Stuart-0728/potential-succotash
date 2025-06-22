#!/usr/bin/env python3
import psycopg2
import os
import sys
from datetime import datetime
import pytz

# 数据库连接信息
def get_db_params():
    """获取数据库连接参数，优先使用环境变量"""
    return {
        'dbname': os.environ.get('DB_NAME', 'cqnu_association_uxft'),
        'user': os.environ.get('DB_USER', 'cqnu_association_uxft_user'),
        'password': os.environ.get('DB_PASSWORD', ''),
        'host': os.environ.get('DB_HOST', 'dpg-d0sjag49c44c73f7jt4g-a.oregon-postgres.render.com'),
        'port': os.environ.get('DB_PORT', '5432')
    }

def read_sql_script(file_path):
    """读取SQL脚本文件内容"""
    with open(file_path, 'r') as f:
        return f.read()

def main():
    """主函数"""
    print("开始修复PostgreSQL数据库时区问题...")
    
    # 检查SQL脚本文件是否存在
    sql_file = 'scripts/fix_postgres_timezone.sql'
    if not os.path.exists(sql_file):
        print(f"错误: SQL脚本文件 {sql_file} 不存在!")
        return 1
    
    # 读取SQL脚本
    sql_script = read_sql_script(sql_file)
    
    # 获取数据库连接参数
    conn_params = get_db_params()
    
    # 检查密码是否为空
    if not conn_params['password']:
        print("错误: 数据库密码未设置。请通过环境变量DB_PASSWORD设置密码。")
        return 1
    
    try:
        # 连接到数据库
        print("正在连接到PostgreSQL数据库...")
        conn = psycopg2.connect(
            dbname=conn_params['dbname'],
            user=conn_params['user'],
            password=conn_params['password'],
            host=conn_params['host'],
            port=conn_params['port']
        )
        cursor = conn.cursor()
        
        # 检查数据库时区设置
        print("\n==== 修复前数据库时区设置 ====")
        cursor.execute("SHOW timezone;")
        result = cursor.fetchone()
        db_timezone = result[0] if result else "未知"
        print(f"数据库时区: {db_timezone}")
        
        # 检查当前数据库时间
        cursor.execute("SELECT NOW();")
        result = cursor.fetchone()
        db_time = result[0] if result else None
        if db_time:
            print(f"数据库当前时间: {db_time}")
            
            # 获取本地时间（考虑时区）
            beijing_now = datetime.now(pytz.timezone('Asia/Shanghai'))
            print(f"本地北京时间: {beijing_now}")
            print(f"时间差异: {(beijing_now - db_time).total_seconds() / 3600:.2f} 小时")
        else:
            print("无法获取数据库当前时间")
        
        # 检查活动表中的时间样例
        print("\n==== 修复前活动时间样例 ====")
        cursor.execute("""
        SELECT id, title, start_time, end_time, registration_deadline 
        FROM activities 
        ORDER BY created_at DESC 
        LIMIT 3;
        """)
        activities = cursor.fetchall()
        
        for activity in activities:
            if len(activity) >= 5:
                id, title, start_time, end_time, reg_deadline = activity
                print(f"\n活动 ID: {id}, 标题: {title}")
                print(f"开始时间: {start_time}")
                print(f"结束时间: {end_time}")
                print(f"报名截止: {reg_deadline}")
        
        # 执行SQL脚本
        print("\n==== 执行时区修复脚本 ====")
        
        # 将脚本分割为单独的语句
        statements = sql_script.split(';')
        
        for statement in statements:
            # 跳过空语句
            if not statement.strip():
                continue
                
            # 打印当前执行的语句（仅显示前100个字符）
            print(f"执行: {statement.strip()[:100]}...")
            
            # 执行语句
            cursor.execute(statement)
        
        # 提交更改
        conn.commit()
        print("所有SQL语句已执行完成并提交。")
        
        # 检查修复后的数据库时区设置
        print("\n==== 修复后数据库时区设置 ====")
        cursor.execute("SHOW timezone;")
        result = cursor.fetchone()
        db_timezone = result[0] if result else "未知"
        print(f"数据库时区: {db_timezone}")
        
        # 检查修复后的活动表中的时间样例
        print("\n==== 修复后活动时间样例 ====")
        cursor.execute("""
        SELECT id, title, start_time, end_time, registration_deadline 
        FROM activities 
        WHERE id IN (SELECT id FROM activities ORDER BY created_at DESC LIMIT 3);
        """)
        activities = cursor.fetchall()
        
        for activity in activities:
            if len(activity) >= 5:
                id, title, start_time, end_time, reg_deadline = activity
                print(f"\n活动 ID: {id}, 标题: {title}")
                print(f"开始时间: {start_time}")
                print(f"结束时间: {end_time}")
                print(f"报名截止: {reg_deadline}")
                
                # 转换为北京时间显示
                if start_time:
                    beijing_start = start_time.astimezone(pytz.timezone('Asia/Shanghai'))
                    print(f"开始时间(北京): {beijing_start.strftime('%Y-%m-%d %H:%M:%S %Z%z')}")
        
        print("\n时区修复完成!")
        
    except Exception as e:
        print(f"错误: {e}")
        return 1
    finally:
        # 关闭连接
        if 'conn' in locals() and conn:
            conn.close()
            print("\n数据库连接已关闭")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 