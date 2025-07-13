#!/usr/bin/env python3
"""
更新配置文件以使用PostgreSQL数据库
"""
import os
import sys

def update_config(pg_uri):
    """更新配置文件使用PostgreSQL"""
    config_path = 'src/config.py'
    
    if not os.path.exists(config_path):
        print(f"错误: 配置文件不存在: {config_path}")
        return False
    
    try:
        # 读取配置文件
        with open(config_path, 'r', encoding='utf-8') as f:
            config_content = f.read()
        
        # 制作备份
        backup_path = f"{config_path}.bak"
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        print(f"已创建配置文件备份: {backup_path}")
        
        # 更新数据库配置
        new_config = []
        lines = config_content.splitlines()
        
        for line in lines:
            # 跳过原始SQLite配置
            if "DB_PATH = os.path.join(INSTANCE_PATH, 'cqnu_association.db')" in line:
                line = "    # DB_PATH = os.path.join(INSTANCE_PATH, 'cqnu_association.db')  # SQLite已弃用"
            
            # 替换数据库URL配置
            if "SQLALCHEMY_DATABASE_URI = f'sqlite:///{DB_PATH}'" in line:
                line = f"    SQLALCHEMY_DATABASE_URI = '{pg_uri}'  # 使用PostgreSQL数据库"
            
            # 禁用SQLite特定设置
            if "'connect_args': {'check_same_thread': False}" in line:
                line = "        # 'connect_args': {'check_same_thread': False} if 'sqlite:' in str(SQLALCHEMY_DATABASE_URI) else {},"
                line += "\n        'connect_args': {},"
            
            # 设置PostgreSQL时区
            if "if 'postgresql:' in str(SQLALCHEMY_DATABASE_URI):" in line:
                line = "    # PostgreSQL时区设置"
                line += "\n    SQLALCHEMY_ENGINE_OPTIONS['connect_args'] = {"
                line += "\n        'options': '-c timezone=UTC'  # 强制PostgreSQL连接使用UTC时区"
                line += "\n    }"
                line += "\n    "
            
            new_config.append(line)
        
        # 写回文件
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_config))
        
        print(f"配置文件已更新: {config_path}")
        return True
    
    except Exception as e:
        print(f"错误: 更新配置文件失败: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python3 update_config_postgres.py <PostgreSQL连接URI>")
        print("示例: python3 update_config_postgres.py postgresql://username:password@localhost:5432/cqnu_association")
        sys.exit(1)
    
    pg_uri = sys.argv[1]
    if update_config(pg_uri):
        print("配置更新成功！请重启应用以使用PostgreSQL数据库")
        sys.exit(0)
    else:
        print("配置更新失败")
        sys.exit(1) 