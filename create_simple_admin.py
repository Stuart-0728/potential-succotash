import os
import sys
import logging
from datetime import datetime
import sqlite3
from werkzeug.security import generate_password_hash

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'cqnu_association.db')

def create_admin():
    # 管理员信息
    username = 'admin2'  # 修改为新的用户名
    password = 'admin123'
    email = 'admin2@example.com'
    
    print(f"使用数据库: {DB_PATH}")
    
    try:
        # 连接到SQLite数据库
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 检查用户是否已存在
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        
        if user:
            logger.info(f"管理员用户 {username} 已存在")
            return
        
        # 获取管理员角色ID
        cursor.execute("SELECT id FROM roles WHERE name = 'admin'")
        role = cursor.fetchone()
        
        if not role:
            # 如果没有admin角色，创建一个
            cursor.execute("INSERT INTO roles (name, description) VALUES (?, ?)", 
                          ('admin', '管理员'))
            conn.commit()
            role_id = cursor.lastrowid
        else:
            role_id = role[0]
        
        # 获取表结构信息
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"用户表列: {columns}")
        
        # 创建管理员用户
        now = datetime.now()
        hashed_password = generate_password_hash(password)
        
        # 构建动态 SQL 语句
        sql = """
            INSERT INTO users (username, email, password_hash, role_id, active, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        
        cursor.execute(sql, (username, email, hashed_password, role_id, 1, now))
        
        conn.commit()
        logger.info(f"管理员用户 {username} 创建成功，密码为 {password}")
        
    except Exception as e:
        logger.error(f"创建管理员用户失败: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    create_admin() 