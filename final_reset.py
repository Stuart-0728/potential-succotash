# final_reset.py - A robust script to completely reset the database.
import os
import sys
from src import create_app, db
# Import all your models here to ensure db.create_all() knows about them
from src.models import User, Role, Activity, StudentInfo, Tag, Registration, PointsHistory, ActivityReview, ActivityCheckin, Message, Notification, NotificationRead, AIChatHistory, AIChatSession, AIUserPreferences
from werkzeug.security import generate_password_hash

# This script uses the SAME .env file as your main application.
# Make sure your .env file is configured with the Render PostgreSQL URL.
app = create_app()

with app.app_context():
    print("="*50)
    print("==== 最终数据库重置与初始化工具 ====")
    print("="*50)
    
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '未找到')
    if 'sqlite' in db_uri:
        print(f"错误: 检测到正在使用SQLite数据库: {db_uri}")
        print("请确保你的 .env 文件已正确配置并被加载。")
        sys.exit(1) # Exit if using the wrong database

    print(f"将要操作的数据库: ...{db_uri[-40:]}") # Show last part of URI for confirmation

    user_input = input("\n警告：此操作将删除数据库中的所有表并丢失所有数据！\n确定要继续吗? (输入 'yes' 确认): ")
    
    if user_input.lower() != 'yes':
        print("\n操作已取消。")
        sys.exit(0)
    
    try:
        print("\n正在删除所有旧表...")
        # drop_all() is the standard way, it respects dependencies
        db.drop_all()
        print("✅ 所有旧表已删除。")

        print("\n正在根据最新模型创建新表...")
        db.create_all()
        print("✅ 所有新表已创建。")

        print("\n正在创建默认角色和管理员账号...")
        # Create roles
        admin_role = Role(name='Admin', description='管理员角色')
        student_role = Role(name='Student', description='学生角色')
        db.session.add_all([admin_role, student_role])
        
        # Create admin user
        admin_user = User(
            username='stuart',
            email='stuart@example.com',
            role_id=1,
            active=True
        )
        admin_user.password = 'LYXspassword123'
        db.session.add(admin_user)
        
        db.session.commit()
        print("✅ 角色 'Admin', 'Student' 已创建。")
        print("✅ 管理员 'stuart' (密码: LYXspassword123) 已创建。")
        
        print("\n" + "="*50)
        print("🎉 操作成功完成！数据库已准备就绪。")
        print("="*50)

    except Exception as e:
        print(f"\n❌ 操作过程中发生严重错误: {e}")
        print("正在回滚所有操作...")
        db.session.rollback()
        print("操作已回滚。数据库可能处于不一致状态，建议再次运行此脚本。")
        sys.exit(1) 