#!/usr/bin/env python3
"""
将通知时间直接设置为正确的北京时间
这个脚本将通知时间直接设置为指定的值，不再依赖复杂的时区转换
"""
import os
import sys
import psycopg2
import logging
from datetime import datetime, timedelta
import pytz

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 数据库连接信息
DATABASE_URL = 'postgresql://cqnureg2_user:Pz8ZVfyLYOD22fkxp9w2XP7B9LsKAPqE@dpg-d1dugl7gi27c73er9p8g-a.oregon-postgres.render.com/cqnureg2'

def execute_query(cursor, query, description=None, fetch=True):
    """执行SQL查询并打印结果"""
    try:
        if description:
            print(f"\n==== {description} ====")
        
        cursor.execute(query)
        
        if fetch and query.strip().upper().startswith("SELECT"):
            results = cursor.fetchall()
            for row in results:
                print(row)
            return results
        return None
    except Exception as e:
        print(f"执行查询失败: {e}")
        return None

def main():
    """主函数"""
    print("开始设置正确的北京时间...")
    
    try:
        # 连接到数据库
        print(f"正在连接到PostgreSQL数据库...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # 检查数据库时区设置
        execute_query(cursor, "SHOW timezone;", description="当前数据库时区设置")
        
        # 设置数据库时区为UTC
        execute_query(cursor, "SET timezone = 'UTC';", description="设置数据库时区为UTC")
        
        # 检查当前通知时间
        execute_query(cursor, """
        SELECT id, title, created_at 
        FROM notification 
        ORDER BY id ASC;
        """, description="当前通知时间")
        
        # 询问用户是否要继续
        answer = input("\n您看到了当前的通知时间。您想要将第一条通知的时间设置为北京时间 2025-06-25 20:32:10 吗? (y/n): ")
        
        if answer.lower() != 'y':
            print("操作已取消")
            return 0
        
        # 直接设置通知时间为正确的北京时间
        execute_query(cursor, """
        UPDATE notification
        SET created_at = '2025-06-25 20:32:10'::timestamp
        WHERE id = 1;
        """, description="设置通知时间", fetch=False)
        
        # 检查设置后的通知时间
        execute_query(cursor, """
        SELECT id, title, created_at 
        FROM notification 
        ORDER BY id ASC;
        """, description="设置后的通知时间")
        
        # 提交更改
        conn.commit()
        print("\n✅ 时间设置完成并已提交更改!")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        return 1
    finally:
        if 'conn' in locals() and conn:
            conn.close()
            print("数据库连接已关闭")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 