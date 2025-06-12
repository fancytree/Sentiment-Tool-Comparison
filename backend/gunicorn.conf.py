# Gunicorn 配置文件
import os

# 服务器套接字
bind = f"0.0.0.0:{os.getenv('PORT', 8001)}"
backlog = 2048

# 工作进程
workers = 1  # 减少工作进程数量以节省内存
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
timeout = 120  # 增加超时时间以允许模型加载
keepalive = 2
graceful_timeout = 120  # 优雅关闭超时时间

# 内存优化
max_requests = 1000  # 每个工作进程处理的最大请求数
max_requests_jitter = 50  # 随机化重启
preload_app = False  # 不预加载应用以节省内存

# 日志
loglevel = "info"
accesslog = "-"
errorlog = "-"

# 进程命名
proc_name = "sentiment-analysis-api"

# 临时目录设置（兼容不同操作系统）
import tempfile
worker_tmp_dir = tempfile.gettempdir() 