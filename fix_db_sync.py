#!/usr/bin/env python3
# 数据库同步修复脚本

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# 数据库连接信息
DB_URL = os.environ.get('DATABASE_URL', 'sqlite:///instance/cqnu_association.db')

def check_and_fix_db():
    """检查并修复数据库结构"""
    try:
        # 创建数据库引擎
        engine = create_engine(DB_URL)
        
        # 检查activities表是否存在
        with engine.connect() as conn:
            print("正在检查数据库连接...")
            
            # 检查activities表结构
            print("正在检查activities表结构...")
            
            # 检查checkin_key列是否存在
            check_column_sql = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='activities' AND column_name='checkin_key';
            """
            
            result = conn.execute(text(check_column_sql))
            columns = result.fetchall()
            
            if not columns:
                print("缺少checkin_key列，正在添加...")
                conn.execute(text("ALTER TABLE activities ADD COLUMN checkin_key VARCHAR(32);"))
                print("checkin_key列添加成功")
            else:
                print("checkin_key列已存在")
                
            # 检查checkin_key_expires列是否存在
            check_column_sql = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='activities' AND column_name='checkin_key_expires';
            """
            
            result = conn.execute(text(check_column_sql))
            columns = result.fetchall()
            
            if not columns:
                print("缺少checkin_key_expires列，正在添加...")
                conn.execute(text("ALTER TABLE activities ADD COLUMN checkin_key_expires TIMESTAMP;"))
                print("checkin_key_expires列添加成功")
            else:
                print("checkin_key_expires列已存在")
                
            conn.commit()
            print("数据库结构检查和修复完成")
            
    except SQLAlchemyError as e:
        print(f"数据库操作错误: {e}")
        return False
    except Exception as e:
        print(f"发生未知错误: {e}")
        return False
        
    return True

if __name__ == "__main__":
    print("开始执行数据库同步修复...")
    success = check_and_fix_db()
    if success:
        print("修复成功")
        sys.exit(0)
    else:
        print("修复失败")
        sys.exit(1) 