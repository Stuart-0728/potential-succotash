import multiprocessing
import os

# 绑定地址和端口
bind = "0.0.0.0:" + os.getenv("PORT", "10000")

# 工作进程数
workers = 4

# 工作模式
worker_class = "sync"

# 超时设置
timeout = 120

# 最大请求数
max_requests = 2000
max_requests_jitter = 200

# 日志配置
accesslog = "-"
errorlog = "-"
loglevel = "info"

# 进程名称
proc_name = "cqnu_association"

# 保持连接
keepalive = 5

# 优雅重启
graceful_timeout = 10

# 守护进程
daemon = False

# 重载
reload = True

# 安全设置
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# 应用加载前的钩子
def on_starting(server):
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info("服务器启动中...")

# 工作进程启动时的钩子
def when_ready(server):
    import logging
    logger = logging.getLogger(__name__)
    logger.info("服务器就绪，可以接受请求")

# 工作进程启动后的钩子
def post_worker_init(worker):
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"工作进程 {worker.pid} 已初始化")

# 确保环境变量
def on_exit(server):
    import logging
    logger = logging.getLogger(__name__)
    logger.info("服务器关闭")
