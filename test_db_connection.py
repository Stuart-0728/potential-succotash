import os
import sys
from sqlalchemy import create_engine, text
import time

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 从配置文件中获取数据库连接字符串
try:
    from src.config import Config
    DATABASE_URL = Config.SQLALCHEMY_DATABASE_URI
    print(f"从配置文件中获取到连接字符串: {DATABASE_URL}")
except Exception as e:
    print(f"错误：无法从配置文件获取数据库连接字符串: {e}")
    sys.exit(1)

print(f"正在尝试使用以下连接字符串连接数据库：\n{DATABASE_URL}\n")

# SQLAlchemy 要求将 postgres:// 替换为 postgresql://
if isinstance(DATABASE_URL, str) and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = None
try:
    # 创建数据库引擎，设置一个10秒的连接超时
    print("正在创建数据库引擎...")
    connect_args = {'check_same_thread': False} if 'sqlite:' in DATABASE_URL else {'connect_timeout': 10}
    engine = create_engine(DATABASE_URL, connect_args=connect_args)
    
    print("正在尝试连接...")
    start_time = time.time()
    
    # 尝试建立连接并执行一个简单的查询
    with engine.connect() as connection:
        end_time = time.time()
        print(f"连接成功！耗时 {end_time - start_time:.2f} 秒。")
        
        if 'sqlite:' in DATABASE_URL:
            result = connection.execute(text("SELECT sqlite_version()"))
        else:
            result = connection.execute(text("SELECT version()"))
        db_version = result.scalar()
        print(f"数据库版本: {db_version}")

except Exception as e:
    end_time = time.time()
    print(f"数据库连接失败！耗时 {end_time - start_time:.2f} 秒。")
    print(f"发生的错误: {e}")
finally:
    if engine:
        engine.dispose()
        print("引擎资源已释放。") 