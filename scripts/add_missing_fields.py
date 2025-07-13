import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from src import db
from flask import Flask
from sqlalchemy import text

def add_missing_fields():
    """添加缺失的数据库字段"""
    try:
        # 添加 notification 表的 is_public 字段
        with db.engine.connect() as conn:
            # 检查字段是否已存在
            result = conn.execute(text("PRAGMA table_info(notification)"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'is_public' not in columns:
                print("添加 notification 表的 is_public 字段...")
                conn.execute(text("ALTER TABLE notification ADD COLUMN is_public BOOLEAN DEFAULT 1"))
                print("成功添加 is_public 字段")
            else:
                print("is_public 字段已存在，无需添加")
        
        return True
    except Exception as e:
        print(f"添加缺失字段时出错: {e}")
        return False

if __name__ == "__main__":
    # 创建一个简单的Flask应用上下文
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../instance/cqnu_association.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    with app.app_context():
        from src.models import db
        db.init_app(app)
        
        # 执行添加字段操作
        success = add_missing_fields()
        
        if success:
            print("所有缺失字段已成功添加!")
        else:
            print("添加缺失字段时出错，请检查日志") 