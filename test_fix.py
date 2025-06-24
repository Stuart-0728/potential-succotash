#!/usr/bin/env python3
"""
测试修复是否生效
"""

import os
import sqlite3
import requests
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_database_columns():
    """检查数据库列是否已添加"""
    try:
        db_path = os.path.join('instance', 'cqnu_association.db')
        if not os.path.exists(db_path):
            logger.error(f"数据库文件不存在: {db_path}")
            return False
        
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查users表的列
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # 检查必要的列是否存在
        required_columns = ['active', 'is_admin', 'last_login']
        missing_columns = [col for col in required_columns if col not in columns]
        
        if missing_columns:
            logger.error(f"users表仍然缺少以下列: {', '.join(missing_columns)}")
            return False
        else:
            logger.info("users表所有必要的列都已存在")
        
        # 关闭连接
        conn.close()
        return True
    
    except Exception as e:
        logger.error(f"检查数据库列时出错: {e}")
        return False

def test_login():
    """测试登录功能"""
    try:
        # 发送登录请求
        url = "http://localhost:8080/login"
        response = requests.get(url)
        
        if response.status_code == 200:
            logger.info("成功访问登录页面")
            
            # 尝试登录
            login_data = {
                'username': 'stuart',
                'password': 'LYXspassword123',
                'remember': 'on'
            }
            
            session = requests.Session()
            response = session.post(url, data=login_data, allow_redirects=True)
            
            if response.url.endswith('admin/dashboard') or response.url.endswith('dashboard'):
                logger.info("登录成功！")
                return True
            else:
                logger.error(f"登录失败，重定向到了: {response.url}")
                return False
        else:
            logger.error(f"访问登录页面失败: {response.status_code}")
            return False
    
    except Exception as e:
        logger.error(f"测试登录时出错: {e}")
        return False

def check_server_status():
    """检查服务器状态"""
    try:
        response = requests.get("http://localhost:8080/")
        if response.status_code == 200:
            logger.info("服务器正常运行")
            return True
        else:
            logger.error(f"服务器返回了非200状态码: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"连接服务器时出错: {e}")
        return False

if __name__ == "__main__":
    logger.info("开始测试修复结果")
    
    # 检查服务器状态
    if not check_server_status():
        logger.error("服务器未正常运行，请确保应用已启动")
    else:
        # 检查数据库列
        if check_database_columns():
            logger.info("数据库列检查通过")
        else:
            logger.error("数据库列检查失败")
        
        # 测试登录
        if test_login():
            logger.info("登录测试通过")
        else:
            logger.error("登录测试失败")
    
    logger.info("测试完成") 