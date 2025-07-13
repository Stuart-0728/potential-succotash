#!/usr/bin/env python3
# 为现有用户创建AI用户偏好设置记录

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# 数据库连接信息
DB_URL = os.environ.get('DATABASE_URL', 'sqlite:///instance/cqnu_association.db')

def create_ai_preferences():
    """为所有现有用户创建AI用户偏好设置记录"""
    try:
        # 创建数据库引擎
        engine = create_engine(DB_URL)
        
        # 连接数据库
        with engine.connect() as conn:
            print("正在检查数据库连接...")
            
            # 检查用户数量
            user_count_result = conn.execute(text("SELECT COUNT(*) FROM users;"))
            user_count = user_count_result.scalar() or 0
            print(f"发现 {user_count} 个用户")
            
            # 检查现有的AI用户偏好设置记录数量
            prefs_count_result = conn.execute(text("SELECT COUNT(*) FROM ai_user_preferences;"))
            prefs_count = prefs_count_result.scalar() or 0
            print(f"发现 {prefs_count} 条AI用户偏好设置记录")
            
            # 如果用户数量大于偏好设置记录数量，则需要添加缺失的记录
            if user_count > prefs_count:
                # 获取所有没有偏好设置记录的用户ID
                missing_users_result = conn.execute(text("""
                    SELECT id, role_id FROM users 
                    WHERE id NOT IN (SELECT user_id FROM ai_user_preferences);
                """))
                missing_users = missing_users_result.fetchall()
                
                print(f"发现 {len(missing_users)} 个用户缺少AI偏好设置记录")
                
                # 为每个缺失的用户创建偏好设置记录
                for user in missing_users:
                    user_id = user[0]
                    role_id = user[1]
                    
                    # 管理员用户可以存储更多历史记录
                    max_history = 100 if role_id == 1 else 50
                    
                    # 插入新记录
                    conn.execute(text("""
                        INSERT INTO ai_user_preferences (user_id, enable_history, max_history_count)
                        VALUES (:user_id, :enable_history, :max_history_count);
                    """), {
                        'user_id': user_id,
                        'enable_history': True,
                        'max_history_count': max_history
                    })
                
                conn.commit()
                print(f"成功为 {len(missing_users)} 个用户创建AI偏好设置记录")
            else:
                print("所有用户都已有AI偏好设置记录，无需操作")
            
            # 确认最终结果
            final_count_result = conn.execute(text("SELECT COUNT(*) FROM ai_user_preferences;"))
            final_count = final_count_result.scalar()
            print(f"当前共有 {final_count} 条AI用户偏好设置记录")
            
            return True
    
    except SQLAlchemyError as e:
        print(f"数据库操作错误: {e}")
        return False
    except Exception as e:
        print(f"发生未知错误: {e}")
        return False

if __name__ == "__main__":
    print("开始为现有用户创建AI用户偏好设置记录...")
    success = create_ai_preferences()
    if success:
        print("操作成功完成")
        sys.exit(0)
    else:
        print("操作失败")
        sys.exit(1) 