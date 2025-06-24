import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

def test_password():
    # 获取数据库路径
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'cqnu_association.db')
    
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return False
    
    # 连接数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 测试密码
        cursor.execute("SELECT password_hash FROM users WHERE username = 'admin'")
        password_hash = cursor.fetchone()[0]
        
        print(f"当前密码哈希: {password_hash}")
        
        # 测试各种密码
        test_passwords = ["admin", "password", "123456", "Admin", "admin123"]
        
        for pwd in test_passwords:
            result = check_password_hash(password_hash, pwd)
            print(f"密码 '{pwd}' 验证结果: {result}")
        
        # 创建新的密码哈希
        plain_password = "simple"
        new_hash = generate_password_hash(plain_password)
        print(f"\n新生成的密码哈希 (密码='{plain_password}'): {new_hash}")
        print(f"验证新密码: {check_password_hash(new_hash, plain_password)}")
        
        # 更新admin用户的密码
        cursor.execute("UPDATE users SET password_hash = ? WHERE username = 'admin'", (new_hash,))
        conn.commit()
        
        print(f"\n已将admin用户密码更新为: '{plain_password}'")
        return True
    except Exception as e:
        conn.rollback()
        print(f"测试密码失败: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    test_password() 