import os
import sys
import sqlite3
from werkzeug.security import generate_password_hash

def reset_database():
    # 获取数据库路径
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'cqnu_association.db')
    
    # 确保instance目录存在
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # 如果数据库文件存在，则删除它
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"已删除旧数据库: {db_path}")
    
    # 创建新的数据库连接
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 创建角色表
    cursor.execute('''
    CREATE TABLE roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT
    )
    ''')
    
    # 创建用户表
    cursor.execute('''
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE,
        password_hash TEXT NOT NULL,
        role_id INTEGER,
        active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP,
        FOREIGN KEY (role_id) REFERENCES roles (id)
    )
    ''')
    
    # 创建系统日志表
    cursor.execute('''
    CREATE TABLE system_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT,
        details TEXT,
        ip_address TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # 插入角色数据
    cursor.execute("INSERT INTO roles (name, description) VALUES (?, ?)", ('Admin', '管理员'))
    cursor.execute("INSERT INTO roles (name, description) VALUES (?, ?)", ('Student', '学生'))
    
    # 获取Admin角色ID
    cursor.execute("SELECT id FROM roles WHERE name = 'Admin'")
    admin_role_id = cursor.fetchone()[0]
    
    # 插入管理员用户
    password_hash = generate_password_hash('LYXspassword123')
    cursor.execute(
        "INSERT INTO users (username, email, password_hash, role_id) VALUES (?, ?, ?, ?)",
        ('stuart', 'admin@example.com', password_hash, admin_role_id)
    )
    
    # 提交更改并关闭连接
    conn.commit()
    conn.close()
    
    print("数据库已重置，管理员账号已创建：")
    print("用户名: stuart")
    print("密码: LYXspassword123")
    print(f"数据库路径: {db_path}")

if __name__ == '__main__':
    reset_database() 