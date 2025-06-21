import os
import logging
from logging.handlers import RotatingFileHandler
import secrets
import pytz

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(16)
    
    # 数据库配置
    # 检测是否在Render上运行
    IS_RENDER_ENVIRONMENT = os.environ.get('RENDER', False) or os.environ.get('IS_RENDER', False)
    
    # 如果存在 DATABASE_URL 环境变量（Render平台提供），则使用它，否则使用SQLite
    database_url = os.environ.get('DATABASE_URL')
    if database_url and database_url.startswith('postgres://'):
        # 将 postgres:// 替换为 postgresql:// 以符合 SQLAlchemy 要求
        SQLALCHEMY_DATABASE_URI = database_url.replace('postgres://', 'postgresql://')
    else:
        SQLALCHEMY_DATABASE_URI = database_url or 'sqlite:///' + os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'instance', 'cqnu_association.db')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 文件上传路径
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src/static/uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'}
    
    # 日志配置
    LOG_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src/logs')
    LOG_LEVEL = logging.INFO
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # 每页显示的记录数
    POSTS_PER_PAGE = 10
    
    # 时区设置
    TIMEZONE = 'Asia/Shanghai'
    
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300
    # 添加时区名称，方便在模板中使用
    TIMEZONE_NAME = 'Asia/Shanghai'
    
    # SQLite 连接配置
    @staticmethod
    def get_sqlite_uri(db_path):
        """获取sqlite数据库URI"""
        return f'sqlite:///{db_path}'
    
    @staticmethod
    def get_postgres_uri():
        """获取PostgreSQL数据库URI"""
        user = os.environ.get('DB_USER', 'postgres')
        password = os.environ.get('DB_PASSWORD', '')
        host = os.environ.get('DB_HOST', 'localhost')
        port = os.environ.get('DB_PORT', '5432')
        db = os.environ.get('DB_NAME', 'cqnu_association')
        return f'postgresql://{user}:{password}@{host}:{port}/{db}'
    
    @staticmethod
    def get_engine_options():
        """获取数据库引擎选项"""
        uri = os.environ.get('DATABASE_URL', '')
        if uri and 'sqlite' in uri:
            return {}
        else:
            # 为PostgreSQL添加时区设置
            return {
                'connect_args': {'timezone': '+08:00'}
            } 

    @staticmethod
    def init_app(app):
        """初始化应用程序"""
        # 确保日志目录存在
        if not os.path.exists(Config.LOG_FOLDER):
            os.makedirs(Config.LOG_FOLDER)
        
        # 配置文件日志
        file_handler = RotatingFileHandler(
            os.path.join(Config.LOG_FOLDER, 'cqnu_association.log'),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(Config.LOG_FORMAT))
        file_handler.setLevel(Config.LOG_LEVEL)
        
        # 配置控制台日志
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(Config.LOG_FORMAT))
        console_handler.setLevel(Config.LOG_LEVEL)
        
        # 将处理器添加到应用日志记录器
        app.logger.addHandler(file_handler)
        app.logger.addHandler(console_handler)
        app.logger.setLevel(Config.LOG_LEVEL)
        
        # 确保上传目录存在
        if not os.path.exists(Config.UPLOAD_FOLDER):
            os.makedirs(Config.UPLOAD_FOLDER)
            
        # 添加Render环境标识和时区配置
        app.config['IS_RENDER_ENVIRONMENT'] = Config.IS_RENDER_ENVIRONMENT
        app.config['TIMEZONE'] = Config.TIMEZONE
        
        if Config.IS_RENDER_ENVIRONMENT:
            app.logger.info("检测到Render环境，已启用特定配置")
            app.logger.info(f"系统时区设置: {Config.TIMEZONE}")

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    LOG_LEVEL = logging.WARNING

class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
} 