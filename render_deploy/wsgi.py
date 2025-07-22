"""
WSGI配置文件 - 用于Render部署
"""
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import create_app

# 创建应用实例
app = create_app()

if __name__ == "__main__":
    app.run()
