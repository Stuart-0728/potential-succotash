#!/usr/bin/env python3
# 模型同步修复脚本

import os
import sys
from sqlalchemy import create_engine, text, MetaData, Table, Column, String, DateTime
from sqlalchemy.exc import SQLAlchemyError

# 数据库连接信息
DB_URL = os.environ.get('DATABASE_URL', 'postgresql://cqnu_association_uxft_user:BamPWSRTgj0sPGKM4sGsLDv8sGCPCPzB@dpg-d0sjag49c44c73f7jt4g-a.oregon-postgres.render.com/cqnu_association_uxft')

def fix_model_sync():
    """强制刷新SQLAlchemy模型"""
    try:
        # 创建数据库引擎
        engine = create_engine(DB_URL)
        
        # 使用元数据反射现有表结构
        metadata = MetaData()
        metadata.reflect(bind=engine)
        
        # 获取activities表
        if 'activities' in metadata.tables:
            activities_table = metadata.tables['activities']
            
            # 检查列是否存在
            has_checkin_key = 'checkin_key' in activities_table.columns
            has_checkin_key_expires = 'checkin_key_expires' in activities_table.columns
            
            print(f"检查activities表结构:")
            print(f"- checkin_key列: {'存在' if has_checkin_key else '不存在'}")
            print(f"- checkin_key_expires列: {'存在' if has_checkin_key_expires else '不存在'}")
            
            # 如果列不存在，添加它们
            with engine.begin() as conn:
                if not has_checkin_key:
                    print("添加checkin_key列...")
                    conn.execute(text("ALTER TABLE activities ADD COLUMN checkin_key VARCHAR(32);"))
                
                if not has_checkin_key_expires:
                    print("添加checkin_key_expires列...")
                    conn.execute(text("ALTER TABLE activities ADD COLUMN checkin_key_expires TIMESTAMP;"))
                
                if not has_checkin_key or not has_checkin_key_expires:
                    print("列添加完成")
        else:
            print("错误: activities表不存在")
            return False
        
        # 导出表结构以确认更改
        with engine.connect() as conn:
            result = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'activities';"))
            columns = result.fetchall()
            
            print("\n当前activities表结构:")
            for column in columns:
                print(f"- {column[0]}: {column[1]}")
        
        return True
    
    except SQLAlchemyError as e:
        print(f"数据库操作错误: {e}")
        return False
    except Exception as e:
        print(f"发生未知错误: {e}")
        return False

if __name__ == "__main__":
    print("开始修复模型同步问题...")
    success = fix_model_sync()
    if success:
        print("\n修复成功")
        sys.exit(0)
    else:
        print("\n修复失败")
        sys.exit(1) 