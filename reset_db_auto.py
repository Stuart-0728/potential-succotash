#!/usr/bin/env python3
"""
自动重置Render平台上的PostgreSQL数据库
使用预设的凭据，无需手动输入或确认
"""
import os
import sys
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# 预设的数据库连接信息
DB_PARAMS = {
    'dbname': 'cqnu_association_uxft',
    'user': 'cqnu_association_uxft_user',
    'password': 'BamPWSRTgj0sPGKM4sGsLDv8sGCPCPzB',
    'host': 'dpg-d0sjag49c44c73f7jt4g-a.oregon-postgres.render.com',
    'port': '5432'
}

def reset_database():
    """重置数据库，删除所有表格并重建"""
    try:
        # 连接到数据库
        print("正在连接到PostgreSQL数据库...")
        conn = psycopg2.connect(**DB_PARAMS)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # 获取所有表名
        print("获取所有表名...")
        cursor.execute("""
            SELECT tablename
            FROM pg_catalog.pg_tables
            WHERE schemaname = 'public'
        """)
        tables = [row[0] for row in cursor.fetchall()]
        print(f"找到 {len(tables)} 个表格: {', '.join(tables)}")
        
        # 自动确认继续
        print("自动确认重置数据库...")
        
        # 删除所有表格
        print("删除所有表格...")
        for table in tables:
            print(f"  正在删除表格: {table}")
            cursor.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(sql.Identifier(table)))
        
        print("所有表格已删除")
        
        # 执行SQL脚本重建表结构
        print("正在重建数据库结构...")
        with open('reset_render_db.sql', 'r') as f:
            sql_script = f.read()
            cursor.execute(sql_script)
        
        print("\n数据库已重置，表结构已重建")
        print("初始管理员账号: admin")
        print("初始管理员密码: admin123")
        
    except psycopg2.Error as e:
        print(f"数据库错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"发生错误: {e}")
        sys.exit(1)
    finally:
        # 关闭连接
        if 'conn' in locals() and conn:
            conn.close()
            print("\n数据库连接已关闭")

if __name__ == "__main__":
    print("==== Render PostgreSQL 数据库自动重置工具 ====")
    print("警告: 此脚本将删除所有数据表并重置数据库!")
    
    # 重置数据库
    reset_database() 