#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
WSGI入口点，用于启动应用
"""

import os
import sys
import logging
from datetime import datetime
import pytz

# 设置工作目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

# 确保BASE_DIR在sys.path中
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 设置环境变量
os.environ['FLASK_APP'] = 'src'
os.environ['FLASK_ENV'] = 'production'
os.environ['TZ'] = 'Asia/Shanghai'

# 设置火山API密钥
if 'ARK_API_KEY' not in os.environ and 'VOLCANO_API_KEY' in os.environ:
    os.environ['ARK_API_KEY'] = os.environ['VOLCANO_API_KEY']
    logger.info("已将VOLCANO_API_KEY设置为ARK_API_KEY")

# 添加应用路径到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 导入应用
logger.info("正在启动应用...")
from src import create_app

# 创建应用
app = create_app('production')
logger.info("应用创建成功")

# Render需要的WSGI应用对象
def main_handler(event, context):
    return app

# 如果直接运行此脚本，启动开发服务器
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
