#!/usr/bin/env python3
"""
从ClawCloud恢复数据到Render数据库
"""
import os
import sys
from src import create_app, db
from src.models import User, Role
from werkzeug.security import generate_password_hash

def main():
    print("="*60)
    print("==== 从ClawCloud恢复数据到Render数据库 ====")
    print("="*60)
    
    app = create_app()
    
    with app.app_context():
        # 检查数据库配置
        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '未找到')
        backup_uri = app.config.get('BACKUP_DATABASE_URL', '未找到')
        
        print(f"主数据库: ...{db_uri[-50:] if len(db_uri) > 50 else db_uri}")
        print(f"备份数据库: ...{backup_uri[-50:] if len(backup_uri) > 50 else backup_uri}")
        
        if backup_uri == '未找到':
            print("\n❌ 错误：未找到备份数据库配置 (BACKUP_DATABASE_URL)")
            print("请确保在Render环境变量中设置了BACKUP_DATABASE_URL")
            sys.exit(1)
        
        # 检查当前数据库是否为空
        try:
            user_count = User.query.count()
            print(f"\n当前主数据库中的用户数量: {user_count}")
            
            if user_count > 0:
                confirm = input("主数据库不为空，继续恢复将覆盖所有数据。确定继续吗？(输入 'yes' 确认): ")
                if confirm.lower() != 'yes':
                    print("操作已取消。")
                    sys.exit(0)
        except Exception as e:
            print(f"检查数据库状态时出错: {e}")
            print("可能是数据库表不存在，将继续恢复操作...")
        
        # 使用数据库同步功能
        try:
            from src.db_sync import DatabaseSyncer
            
            print("\n开始从ClawCloud恢复数据...")
            syncer = DatabaseSyncer()
            
            # 执行恢复
            success = syncer.restore_from_clawcloud()
            
            if success:
                print("✅ 数据恢复成功！")
                
                # 验证恢复结果
                try:
                    user_count = User.query.count()
                    print(f"恢复后的用户数量: {user_count}")
                    
                    # 检查是否有管理员账户
                    admin_users = User.query.filter_by(role_id=1).all()
                    if admin_users:
                        print("✅ 找到管理员账户:")
                        for admin in admin_users:
                            print(f"  - 用户名: {admin.username}")
                    else:
                        print("⚠️  未找到管理员账户，创建默认管理员...")
                        create_default_admin()
                        
                except Exception as e:
                    print(f"验证恢复结果时出错: {e}")
                    print("数据可能已恢复，但验证失败。请手动检查。")
                
            else:
                print("❌ 数据恢复失败！")
                print("尝试创建基本的管理员账户...")
                create_basic_structure()
                
        except ImportError:
            print("❌ 无法导入数据库同步模块，尝试创建基本结构...")
            create_basic_structure()
        except Exception as e:
            print(f"❌ 恢复过程中出错: {e}")
            print("尝试创建基本的管理员账户...")
            create_basic_structure()

def create_basic_structure():
    """创建基本的数据库结构和管理员账户"""
    try:
        print("\n正在创建基本数据库结构...")
        
        # 创建所有表
        db.create_all()
        print("✅ 数据库表已创建")
        
        # 检查是否已有角色
        admin_role = Role.query.filter_by(name='Admin').first()
        student_role = Role.query.filter_by(name='Student').first()
        
        if not admin_role:
            admin_role = Role(name='Admin', description='管理员角色')
            db.session.add(admin_role)
            print("✅ 创建管理员角色")
        
        if not student_role:
            student_role = Role(name='Student', description='学生角色')
            db.session.add(student_role)
            print("✅ 创建学生角色")
        
        db.session.commit()
        
        # 创建管理员账户
        create_default_admin()
        
    except Exception as e:
        print(f"❌ 创建基本结构失败: {e}")
        db.session.rollback()

def create_default_admin():
    """创建默认管理员账户"""
    try:
        # 检查是否已有管理员
        existing_admin = User.query.filter_by(username='stuart').first()
        if existing_admin:
            print("✅ 管理员账户 'stuart' 已存在")
            return
        
        # 创建管理员账户
        admin_user = User(
            username='stuart',
            email='stuart@example.com',
            role_id=1,
            active=True
        )
        admin_user.password = 'LYXspassword123'
        db.session.add(admin_user)
        db.session.commit()
        
        print("✅ 创建默认管理员账户:")
        print("   用户名: stuart")
        print("   密码: LYXspassword123")
        
    except Exception as e:
        print(f"❌ 创建管理员账户失败: {e}")
        db.session.rollback()

if __name__ == '__main__':
    main()
    
    print("\n" + "="*60)
    print("🎉 操作完成！")
    print("现在你可以:")
    print("1. 访问 https://reg.cqaibase.cn/auth/login")
    print("2. 使用用户名 'stuart' 和密码 'LYXspassword123' 登录")
    print("3. 访问 /admin/database-status 检查数据库状态")
    print("4. 如果需要，可以手动触发数据同步")
    print("="*60)
