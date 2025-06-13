import multiprocessing

# 绑定的IP和端口
bind = "0.0.0.0:10000"

# 工作进程数
workers = multiprocessing.cpu_count() * 2 + 1

# 工作模式
worker_class = "sync"

# 超时时间
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

# 预加载应用
preload_app = True

# 守护进程模式
daemon = False

# 调试模式
reload = False

# 安全设置
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190
