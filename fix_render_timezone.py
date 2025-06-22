#!/usr/bin/env python3
"""
修复Render上的PostgreSQL数据库时区问题
该脚本将在Render环境中运行，修复数据库中的时区问题
"""
import os
import sys
import psycopg2
import logging
import argparse
from datetime import datetime
import pytz

# 设置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 数据库连接信息
def get_db_params():
    """获取数据库连接参数，优先使用环境变量"""
    return {
        'dbname': os.environ.get('DB_NAME', 'cqnu_association_uxft'),
        'user': os.environ.get('DB_USER', 'cqnu_association_uxft_user'),
        'password': os.environ.get('DB_PASSWORD', 'BamPWSRTgj0sPGKM4sGsLDv8sGCPCPzB'),
        'host': os.environ.get('DB_HOST', 'dpg-d0sjag49c44c73f7jt4g-a.oregon-postgres.render.com'),
        'port': os.environ.get('DB_PORT', '5432')
    }

def execute_query(cursor, query, params=None, description=None):
    """执行SQL查询并打印结果"""
    if description:
        print(f"\n>>> {description}")
    
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        if query.strip().upper().startswith("SELECT"):
            results = cursor.fetchall()
            if results:
                for row in results:
                    print(row)
            else:
                print("查询没有返回结果")
        else:
            print("查询执行成功")
    except Exception as e:
        print(f"执行查询时出错: {e}")

def main():
    """主函数"""
    print("开始修复Render环境中的时区问题...")
    
    # 获取数据库连接参数
    conn_params = get_db_params()
    
    # 检查密码是否为空
    if not conn_params['password']:
        print("错误: 数据库密码未设置。请通过环境变量DB_PASSWORD设置密码。")
        return 1
    
    try:
        # 连接到数据库
        print(f"正在连接到PostgreSQL数据库 {conn_params['host']}...")
        conn = psycopg2.connect(
            dbname=conn_params['dbname'],
            user=conn_params['user'],
            password=conn_params['password'],
            host=conn_params['host'],
            port=conn_params['port']
        )
        cursor = conn.cursor()
        
        # 检查数据库时区设置
        execute_query(cursor, "SHOW timezone;", description="当前数据库时区设置")
        
        # 设置数据库时区为UTC
        execute_query(cursor, "SET timezone = 'UTC';", description="设置数据库时区为UTC")
        
        # 检查设置后的时区
        execute_query(cursor, "SHOW timezone;", description="设置后的数据库时区")
        
        # 检查当前数据库时间
        execute_query(cursor, "SELECT NOW();", description="当前数据库时间")
        
        # 检查活动表中的时间样例（修复前）
        execute_query(cursor, """
        SELECT id, title, start_time, end_time, registration_deadline 
        FROM activities 
        ORDER BY created_at DESC 
        LIMIT 3;
        """, description="修复前的活动时间样例")
        
        # 执行时区修复
        print("\n开始执行时区修复...")
        
        # 1. 修复活动表中的时间字段
        execute_query(cursor, """
        UPDATE activities
        SET start_time = start_time AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
        WHERE start_time IS NOT NULL;
        """, description="修复活动开始时间")
        
        execute_query(cursor, """
        UPDATE activities
        SET end_time = end_time AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
        WHERE end_time IS NOT NULL;
        """, description="修复活动结束时间")
        
        execute_query(cursor, """
        UPDATE activities
        SET registration_deadline = registration_deadline AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
        WHERE registration_deadline IS NOT NULL;
        """, description="修复活动报名截止时间")
        
        execute_query(cursor, """
        UPDATE activities
        SET created_at = created_at AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
        WHERE created_at IS NOT NULL;
        """, description="修复活动创建时间")
        
        execute_query(cursor, """
        UPDATE activities
        SET updated_at = updated_at AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
        WHERE updated_at IS NOT NULL;
        """, description="修复活动更新时间")
        
        # 2. 修复报名表中的时间字段
        execute_query(cursor, """
        UPDATE registrations
        SET register_time = register_time AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
        WHERE register_time IS NOT NULL;
        """, description="修复报名时间")
        
        execute_query(cursor, """
        UPDATE registrations
        SET check_in_time = check_in_time AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
        WHERE check_in_time IS NOT NULL;
        """, description="修复签到时间")
        
        # 3. 修复通知表中的时间字段
        execute_query(cursor, """
        UPDATE notification
        SET created_at = created_at AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
        WHERE created_at IS NOT NULL;
        """, description="修复通知创建时间")
        
        execute_query(cursor, """
        UPDATE notification
        SET expiry_date = expiry_date AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
        WHERE expiry_date IS NOT NULL;
        """, description="修复通知过期时间")
        
        # 4. 修复通知已读表中的时间字段
        execute_query(cursor, """
        UPDATE notification_read
        SET read_at = read_at AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
        WHERE read_at IS NOT NULL;
        """, description="修复通知已读时间")
        
        # 5. 修复站内信表中的时间字段
        execute_query(cursor, """
        UPDATE message
        SET created_at = created_at AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
        WHERE created_at IS NOT NULL;
        """, description="修复站内信创建时间")
        
        # 6. 修复系统日志表中的时间字段
        execute_query(cursor, """
        UPDATE system_logs
        SET created_at = created_at AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
        WHERE created_at IS NOT NULL;
        """, description="修复系统日志创建时间")
        
        # 7. 修复积分历史表中的时间字段
        execute_query(cursor, """
        UPDATE points_history
        SET created_at = created_at AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
        WHERE created_at IS NOT NULL;
        """, description="修复积分历史创建时间")
        
        # 8. 修复活动评价表中的时间字段
        execute_query(cursor, """
        UPDATE activity_reviews
        SET created_at = created_at AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
        WHERE created_at IS NOT NULL;
        """, description="修复活动评价创建时间")
        
        # 9. 修复AI聊天历史表中的时间字段
        execute_query(cursor, """
        UPDATE ai_chat_history
        SET timestamp = timestamp AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
        WHERE timestamp IS NOT NULL;
        """, description="修复AI聊天历史时间")
        
        # 10. 修复AI聊天会话表中的时间字段
        execute_query(cursor, """
        UPDATE ai_chat_sessions
        SET created_at = created_at AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
        WHERE created_at IS NOT NULL;
        """, description="修复AI聊天会话创建时间")
        
        execute_query(cursor, """
        UPDATE ai_chat_sessions
        SET updated_at = updated_at AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
        WHERE updated_at IS NOT NULL;
        """, description="修复AI聊天会话更新时间")
        
        # 11. 修复用户表中的时间字段
        execute_query(cursor, """
        UPDATE users
        SET created_at = created_at AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
        WHERE created_at IS NOT NULL;
        """, description="修复用户创建时间")
        
        execute_query(cursor, """
        UPDATE users
        SET last_login = last_login AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
        WHERE last_login IS NOT NULL;
        """, description="修复用户最后登录时间")
        
        # 检查活动表中的时间样例（修复后）
        execute_query(cursor, """
        SELECT id, title, start_time, end_time, registration_deadline 
        FROM activities 
        ORDER BY created_at DESC 
        LIMIT 3;
        """, description="修复后的活动时间样例")
        
        # 提交更改
        conn.commit()
        print("\n所有时区修复已成功提交!")
        
    except Exception as e:
        print(f"错误: {e}")
        return 1
    finally:
        # 关闭连接
        if 'conn' in locals() and conn:
            conn.close()
            print("\n数据库连接已关闭")
    
    print("\n时区修复脚本执行完成。请确保应用代码中的时区处理逻辑正确。")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 