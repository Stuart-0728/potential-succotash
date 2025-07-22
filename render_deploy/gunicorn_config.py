"""
Gunicorn配置文件 - 用于Render部署
"""
import os

# 绑定地址和端口
bind = f"0.0.0.0:{os.environ.get('PORT', 10000)}"

# 工作进程数
workers = int(os.environ.get('WEB_CONCURRENCY', 2))

# 工作进程类型
worker_class = "sync"

# 每个工作进程的线程数
threads = int(os.environ.get('THREADS', 2))

# 工作进程超时时间
timeout = int(os.environ.get('TIMEOUT', 120))

# 保持连接时间
keepalive = int(os.environ.get('KEEPALIVE', 5))

# 最大请求数
max_requests = int(os.environ.get('MAX_REQUESTS', 1000))

# 最大请求数抖动
max_requests_jitter = int(os.environ.get('MAX_REQUESTS_JITTER', 100))

# 预加载应用
preload_app = True

# 日志级别
loglevel = os.environ.get('LOG_LEVEL', 'info')

# 访问日志格式
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# 错误日志文件
errorlog = '-'

# 访问日志文件
accesslog = '-'

# 捕获输出
capture_output = True

# 启用访问日志
disable_redirect_access_to_syslog = True
