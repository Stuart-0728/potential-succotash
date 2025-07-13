#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
重置用户密码的脚本
"""

import sys
import os
import logging
from datetime import datetime
import pytz

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 设置工作目录为项目根目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 设置环境变量
os.environ['FLASK_APP'] = 'src'
os.environ['FLASK_ENV'] = 'development'

try:
    # 导入应用和数据库
    from src import db, create_app
    from src.models import User
    
    # 创建应用
    app = create_app()
    
    # 激活应用上下文
    with app.app_context():
        # 查找用户
        username = 'connor'  # 要重置的用户名
        user = User.query.filter_by(username=username).first()
        
        if not user:
            logger.error(f"用户 {username} 不存在")
            sys.exit(1)
        
        # 设置新密码
        new_password = "123456"
        user.password = new_password
        
        # 提交更改
        db.session.commit()
        
        # 验证密码
        if user.verify_password(new_password):
            logger.info(f"用户 {username} 密码已重置为 '{new_password}' 并验证成功")
            print(f"\n用户 {username} 密码已重置为 '{new_password}' 并验证成功\n")
        else:
            logger.error(f"密码验证失败")
            print(f"\n密码设置成功但验证失败，可能是哈希算法问题\n")
        
except Exception as e:
    logger.error(f"重置密码时出错: {e}")
    print(f"重置密码时出错: {e}")
    sys.exit(1) 