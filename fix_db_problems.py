#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复数据库问题脚本
解决SQLAlchemy实例未正确注册到Flask应用的问题
"""

import os
import sys
import logging
import shutil
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def backup_files():
    """备份关键文件"""
    backup_dir = os.path.join('src', 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    files_to_backup = [
        'src/__init__.py',
        'src/models/__init__.py',
        'wsgi.py'
    ]
    
    for file_path in files_to_backup:
        if os.path.exists(file_path):
            backup_path = os.path.join(backup_dir, f"{os.path.basename(file_path)}_{timestamp}")
            shutil.copy2(file_path, backup_path)
            logger.info(f"已备份 {file_path} 到 {backup_path}")
        else:
            logger.warning(f"文件 {file_path} 不存在，跳过备份")
    
    return True

def fix_init_py():
    """修复src/__init__.py文件"""
    file_path = 'src/__init__.py'
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 确保只有一个db实例
        db_instance_line = "db = SQLAlchemy()"
        if content.count(db_instance_line) > 1:
            logger.info("检测到多个SQLAlchemy实例声明，修复中...")
            # 删除重复的db实例声明
            lines = content.split('\n')
            found_first = False
            new_lines = []
            
            for line in lines:
                if db_instance_line in line and not found_first:
                    new_lines.append(line)
                    found_first = True
                elif db_instance_line in line and found_first:
                    # 跳过重复的声明
                    continue
                else:
                    new_lines.append(line)
            
            # 写回文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(new_lines))
            
            logger.info(f"已修复 {file_path}")
        else:
            logger.info(f"{file_path} 不需要修复")
        
        return True
    except Exception as e:
        logger.error(f"修复 {file_path} 时出错: {e}")
        return False

def fix_models_init_py():
    """修复src/models/__init__.py文件"""
    file_path = 'src/models/__init__.py'
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否有db = SQLAlchemy()声明
        db_instance_line = "db = SQLAlchemy()"
        if db_instance_line in content:
            logger.info("检测到models/__init__.py中有SQLAlchemy实例声明，修复中...")
            
            # 替换为从src导入db
            new_content = content.replace(db_instance_line, "# 从src导入db实例\nfrom src import db")
            
            # 写回文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            logger.info(f"已修复 {file_path}")
        else:
            logger.info(f"{file_path} 不需要修复")
        
        return True
    except Exception as e:
        logger.error(f"修复 {file_path} 时出错: {e}")
        return False

def fix_wsgi_py():
    """修复或创建wsgi.py文件"""
    file_path = 'wsgi.py'
    
    try:
        # 创建正确的wsgi.py文件
        content = """import sys
import os

# 将项目根目录添加到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import create_app

app = create_app()

if __name__ == "__main__":
    # 使用端口8080避免与macOS AirPlay服务冲突
    app.run(host='0.0.0.0', port=8080, debug=True)
"""
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"已创建/修复 {file_path}")
        return True
    except Exception as e:
        logger.error(f"修复 {file_path} 时出错: {e}")
        return False

def main():
    """主函数"""
    logger.info("开始修复数据库问题...")
    
    # 备份文件
    if not backup_files():
        logger.error("备份文件失败，终止修复")
        return False
    
    # 修复文件
    if not fix_init_py():
        logger.error("修复 src/__init__.py 失败")
        return False
    
    if not fix_models_init_py():
        logger.error("修复 src/models/__init__.py 失败")
        return False
    
    if not fix_wsgi_py():
        logger.error("修复 wsgi.py 失败")
        return False
    
    logger.info("所有文件修复完成！")
    logger.info("请使用以下命令启动应用：")
    logger.info("python3 wsgi.py")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 