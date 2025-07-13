#!/usr/bin/env python3
"""
重置Render平台上的PostgreSQL数据库
删除所有表格并重新创建数据结构
"""
import os
import sys
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import getpass

def get_db_credentials():
    """获取数据库连接信息，优先从环境变量读取"""
    # 尝试从环境变量中获取数据库连接信息
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url:
        print("从环境变量中获取数据库连接信息...")
        if database_url.startswith('postgres://'):
            # 解析数据库URL
            db_url = database_url.replace('postgres://', '')
            user_pass, host_port_db = db_url.split('@')
            user, password = user_pass.split(':')
            host_port, dbname = host_port_db.split('/')
            if ':' in host_port:
                host, port = host_port.split(':')
            else:
                host = host_port
                port = '5432'
                
            return {
                'dbname': dbname,
                'user': user,
                'password': password,
                'host': host,
                'port': port
            }
    
    # 如果环境变量中没有，则手动输入
    print("请输入Render PostgreSQL数据库连接信息:")
    dbname = input("数据库名: ")
    user = input("用户名: ")
    password = getpass.getpass("密码: ")
    host = input("主机地址: ")
    port = input("端口 (默认5432): ") or '5432'
    
    return {
        'dbname': dbname,
        'user': user,
        'password': password,
        'host': host,
        'port': port
    }

def reset_database(conn_params):
    """重置数据库，删除所有表格并重建"""
    try:
        # 连接到数据库
        print("正在连接到PostgreSQL数据库...")
        conn = psycopg2.connect(**conn_params)
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
        print(f"找到 {len(tables)} 个表格")
        
        # 确认是否继续
        confirmation = input(f"确定要删除所有表格并重置数据库吗? 此操作不可恢复! (yes/no): ")
        if confirmation.lower() != 'yes':
            print("操作已取消")
            return
        
        # 禁用外键约束
        print("禁用外键约束...")
        cursor.execute("SET CONSTRAINTS ALL DEFERRED;")
        
        # 删除所有表格
        print("删除所有表格...")
        for table in tables:
            print(f"  正在删除表格: {table}")
            cursor.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(sql.Identifier(table)))
        
        print("所有表格已删除")
        
        # 重建数据结构 (导入SQL文件或在此处定义表结构)
        print("\n数据库已重置，请通过应用程序初始化数据结构")
        print("推荐启动应用程序，让Flask-Migrate自动创建表结构")
        
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
    print("==== Render PostgreSQL 数据库重置工具 ====")
    print("警告: 此脚本将删除所有数据表并重置数据库!")
    print("请确保已备份重要数据")
    
    # 获取数据库连接信息
    conn_params = get_db_credentials()
    
    # 重置数据库
    reset_database(conn_params) 