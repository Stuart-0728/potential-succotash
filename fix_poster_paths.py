#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
修复数据库中海报路径包含None的问题
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# 导入Flask应用和数据库模型
from src import create_app
from src.models import db, Activity

app = create_app()

def fix_poster_paths():
    """修复数据库中的海报路径"""
    with app.app_context():
        print("开始修复数据库中的海报路径...")
        # 获取所有活动
        activities = Activity.query.all()
        fixed_count = 0
        
        for activity in activities:
            if activity.poster_image and "None" in activity.poster_image:
                old_path = activity.poster_image
                try:
                    # 从文件名中提取时间戳部分
                    parts = old_path.split('_')
                    if len(parts) >= 3:
                        # 替换None为实际活动ID
                        new_path = f"activity_{activity.id}_{parts[2]}"
                        activity.poster_image = new_path
                        print(f"  修复海报路径: {old_path} -> {new_path}")
                        fixed_count += 1
                except Exception as e:
                    print(f"  修复海报路径出错 (ID={activity.id}): {e}")
        
        if fixed_count > 0:
            db.session.commit()
            print(f"已成功修复 {fixed_count} 个海报路径")
        else:
            print("未发现需要修复的海报路径")

if __name__ == "__main__":
    fix_poster_paths() 