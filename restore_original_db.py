import os
import shutil
import sqlite3
from datetime import datetime

def backup_current_db():
    """备份当前数据库"""
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'cqnu_association.db')
    if os.path.exists(db_path):
        backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src', 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(backup_dir, f'db_backup_{timestamp}.db')
        
        shutil.copy2(db_path, backup_path)
        print(f"当前数据库已备份到: {backup_path}")
    else:
        print("当前数据库文件不存在，无需备份")

def reset_db_permissions():
    """重置数据库文件和目录权限"""
    instance_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
    db_path = os.path.join(instance_dir, 'cqnu_association.db')
    
    # 确保目录存在
    os.makedirs(instance_dir, exist_ok=True)
    
    # 设置目录权限
    try:
        os.chmod(instance_dir, 0o777)  # 777权限，确保完全访问
        print(f"已修改数据库目录权限为777: {instance_dir}")
        
        # 如果数据库文件存在，设置其权限
        if os.path.exists(db_path):
            os.chmod(db_path, 0o666)  # 666权限，确保可读写
            print(f"已修改数据库文件权限为666: {db_path}")
    except Exception as e:
        print(f"设置权限时出错: {e}")

def check_db_users():
    """检查数据库中的用户"""
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'cqnu_association.db')
    if not os.path.exists(db_path):
        print("数据库文件不存在")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查用户表
        cursor.execute("SELECT id, username, email, role_id FROM users")
        users = cursor.fetchall()
        
        if users:
            print("\n现有用户列表:")
            print("ID | 用户名 | 邮箱 | 角色ID")
            print("-" * 50)
            for user in users:
                print(f"{user[0]} | {user[1]} | {user[2]} | {user[3]}")
        else:
            print("数据库中没有用户")
            
        conn.close()
    except Exception as e:
        print(f"检查用户时出错: {e}")

if __name__ == "__main__":
    backup_current_db()
    reset_db_permissions()
    check_db_users()
    print("\n数据库已重置权限，请尝试使用原始账户登录。") 