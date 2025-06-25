#!/usr/bin/env python3
"""
测试创建通知，验证时区处理是否正确
"""
import os
import sys
import pytz
from datetime import datetime

# 设置数据库URL环境变量
os.environ['DATABASE_URL'] = 'postgresql://cqnureg2_user:Pz8ZVfyLYOD22fkxp9w2XP7B9LsKAPqE@dpg-d1dugl7gi27c73er9p8g-a.oregon-postgres.render.com/cqnureg2'

def main():
    """主函数"""
    try:
        # 导入应用程序
        from src import create_app, db
        from src.models import Notification, User
        from src.utils.time_helpers import display_datetime
        
        # 创建Flask应用获取数据库上下文
        app = create_app()
        
        with app.app_context():
            print("开始测试创建通知...")
            
            # 获取管理员用户
            admin = db.session.query(User).filter_by(username='stuart').first()
            if not admin:
                print("错误: 找不到管理员用户'stuart'")
                return 1
                
            print(f"使用管理员: {admin.username} (ID: {admin.id})")
            
            # 1. 创建一个带UTC时区的时间
            utc_now = datetime.now(pytz.UTC)
            print(f"当前UTC时间: {utc_now}")
            
            # 2. 转换为北京时间显示
            beijing_now = utc_now.astimezone(pytz.timezone('Asia/Shanghai'))
            print(f"北京时间: {beijing_now}")
            
            # 3. 创建通知
            new_notification = Notification(
                title="时区测试通知",
                content="这是一个用于测试时区处理的通知",
                is_important=True,
                created_at=utc_now,
                created_by=admin.id,
                is_public=True
            )
            
            db.session.add(new_notification)
            db.session.commit()
            print(f"通知已创建, ID: {new_notification.id}")
            
            # 4. 查询并显示所有通知
            notifications = db.session.query(Notification).order_by(Notification.created_at.desc()).all()
            print("\n所有通知:")
            for idx, notif in enumerate(notifications):
                # 使用display_datetime函数格式化时间
                formatted_time = display_datetime(notif.created_at)
                print(f"{idx+1}. [{notif.id}] {notif.title} - {formatted_time}")
                print(f"   原始时间值: {notif.created_at}")
                
            print("\n✅ 测试完成")
                
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 