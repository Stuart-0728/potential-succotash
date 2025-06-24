#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import logging
from datetime import datetime
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# 获取数据库连接URL
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    # 尝试从Render提供的环境变量获取
    DATABASE_URL = os.environ.get('RENDER_DATABASE_URL')

if not DATABASE_URL:
    logger.error("找不到数据库连接URL。请设置DATABASE_URL环境变量。")
    sys.exit(1)

def execute_sql_file(file_path):
    """执行SQL文件"""
    try:
        # 读取SQL文件内容
        with open(file_path, 'r') as f:
            sql_commands = f.read()
        
        # 连接数据库
        logger.info(f"正在连接到数据库...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # 执行SQL命令
        logger.info(f"执行SQL文件: {file_path}")
        cursor.execute(sql_commands)
        
        # 获取结果
        try:
            results = cursor.fetchall()
            for row in results:
                logger.info(row[0])
        except:
            pass
        
        # 提交事务
        conn.commit()
        logger.info("SQL执行成功")
        
        # 关闭连接
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"执行SQL文件时出错: {e}")
        return False

if __name__ == "__main__":
    sql_file = "scripts/add_poster_image_column.sql"
    
    logger.info(f"开始添加poster_image列到activities表 - {datetime.now()}")
    
    if not os.path.exists(sql_file):
        logger.error(f"SQL文件不存在: {sql_file}")
        sys.exit(1)
    
    success = execute_sql_file(sql_file)
    
    if success:
        logger.info("poster_image列添加成功!")
    else:
        logger.error("添加poster_image列失败")
        sys.exit(1) 