import os
import sys
import psycopg2

# 数据库连接信息
DATABASE_URL = "postgresql://cqnureg2_user:Pz8ZVfyLYOD22fkxp9w2XP7B9LsKAPqE@dpg-d1dugl7gi27c73er9p8g-a.oregon-postgres.render.com/cqnureg2"

print(f"正在连接到数据库...")

try:
    # 连接到PostgreSQL数据库
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # 执行SQL语句修改列类型
    print("正在修改activities表的checkin_key_expires列类型...")
    cursor.execute("ALTER TABLE activities ALTER COLUMN checkin_key_expires TYPE timestamptz;")
    
    # 提交更改
    conn.commit()
    print("成功修改列类型为timestamptz（带时区的时间戳）")
    
    # 关闭连接
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"错误：{e}")
    sys.exit(1)

print("数据库迁移完成！") 