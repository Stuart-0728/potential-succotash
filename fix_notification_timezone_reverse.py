#!/usr/bin/env python3
"""
反向修复PostgreSQL数据库中的通知时区问题
"""
import os
import sys
import psycopg2
import logging
from datetime import datetime
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
    print("开始反向修复通知时区问题...")
    
    try:
        # 连接到数据库
        print(f"正在连接到PostgreSQL数据库...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # 检查数据库时区设置
        execute_query(cursor, "SHOW timezone;", description="当前数据库时区设置")
        
        # 设置数据库时区为UTC
        execute_query(cursor, "SET timezone = 'UTC';", description="设置数据库时区为UTC")
        
        # 检查当前数据库时间
        execute_query(cursor, "SELECT NOW();", description="当前数据库时间")
        
        # 检查通知表中的时间样例（修复前）
        execute_query(cursor, """
        SELECT id, title, created_at, expiry_date 
        FROM notification 
        ORDER BY created_at DESC 
        LIMIT 3;
        """, description="修复前的通知时间样例")
        
        # 执行反向时区修复
        print("\n开始执行通知时区反向修复...")
        
        # 1. 修复通知创建时间 (反向操作)
        execute_query(cursor, """
        UPDATE notification
        SET created_at = created_at AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
        WHERE created_at IS NOT NULL;
        """, description="反向修复通知创建时间")
        
        # 2. 修复通知过期时间 (反向操作)
        execute_query(cursor, """
        UPDATE notification
        SET expiry_date = expiry_date AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
        WHERE expiry_date IS NOT NULL;
        """, description="反向修复通知过期时间")
        
        # 3. 反向修复通知已读表中的时间字段
        execute_query(cursor, """
        UPDATE notification_read
        SET read_at = read_at AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
        WHERE read_at IS NOT NULL;
        """, description="反向修复通知已读时间")
        
        # 查看修复结果
        execute_query(cursor, """
        SELECT id, title, created_at, expiry_date 
        FROM notification 
        ORDER BY created_at DESC 
        LIMIT 3;
        """, description="修复后的通知时间样例")
        
        # 提交更改
        conn.commit()
        print("\n✅ 时区反向修复完成并已提交更改!")
        
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