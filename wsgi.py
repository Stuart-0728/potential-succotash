import sys
import os
import logging
import argparse

# 将项目根目录添加到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 配置基本日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logger.info("正在启动应用...")

try:
    from src import create_app
    app = create_app()
    logger.info("应用创建成功")
except Exception as e:
    logger.error(f"应用创建失败: {e}", exc_info=True)
    raise

if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='启动Flask应用服务器')
    parser.add_argument('--port', type=int, default=8081, help='指定运行端口 (默认: 8081)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='指定主机地址 (默认: 0.0.0.0)')
    parser.add_argument('--debug', action='store_true', default=True, help='是否启用调试模式 (默认: 启用)')
    
    args = parser.parse_args()
    
    # 使用指定的端口
    port = args.port
    host = args.host
    debug = args.debug
    
    logger.info(f"应用将在 http://{host if host != '0.0.0.0' else '127.0.0.1'}:{port} 上运行")
    app.run(host=host, port=port, debug=debug)
