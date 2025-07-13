#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import logging

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - INFO - %(message)s'
)

logger = logging.getLogger(__name__)
logger.info("正在启动应用...")

# 设置环境变量，确保它们在应用创建前被配置
os.environ.setdefault('FLASK_CONFIG', 'production')

# 设置火山API密钥
if 'ARK_API_KEY' not in os.environ and 'VOLCANO_API_KEY' in os.environ:
    os.environ['ARK_API_KEY'] = os.environ['VOLCANO_API_KEY']
    logger.info("已将VOLCANO_API_KEY设置为ARK_API_KEY")

# 添加应用路径到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
logger.info(f"添加路径到Python路径: {parent_dir}")

# 打印当前Python路径以便调试
logger.info(f"Python路径: {sys.path}")

try:
    # 创建应用
    from src import create_app
    app = create_app()
    logger.info("应用创建成功")
except ImportError as e:
    logger.error(f"导入错误: {e}")
    # 尝试列出目录内容
    if os.path.exists(parent_dir):
        logger.info(f"父目录 {parent_dir} 内容: {os.listdir(parent_dir)}")
    if os.path.exists(os.path.join(parent_dir, 'src')):
        logger.info(f"src目录内容: {os.listdir(os.path.join(parent_dir, 'src'))}")
    raise

# Render需要的WSGI应用对象
def main_handler(event, context):
    return app

# 本地运行时使用
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
