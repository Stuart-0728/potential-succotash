import os
import logging
import secrets
from datetime import timedelta
from dotenv import load_dotenv

# 在文件顶部，确保 .env 文件总是在配置被读取前加载
load_dotenv() 

# 基础路径配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTANCE_PATH = os.path.join(BASE_DIR, 'instance')
DB_PATH = os.path.join(INSTANCE_PATH, 'cqnu_association.db')
LOG_PATH = os.path.join(BASE_DIR, 'logs')
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
SESSION_FILE_DIR = os.path.join(BASE_DIR, 'flask_session')

# 确保目录存在并设置权限
def ensure_directories():
    """确保必要的目录存在并设置正确的权限"""
    # 确保instance目录存在
    if not os.path.exists(INSTANCE_PATH):
        try:
            os.makedirs(INSTANCE_PATH, mode=0o755)
            print(f"已创建数据库目录: {INSTANCE_PATH}")
        except Exception as e:
            print(f"创建数据库目录失败: {e}")
    
    # 检查instance目录权限
    try:
        instance_perms = os.stat(INSTANCE_PATH).st_mode & 0o777
        if instance_perms != 0o755:
            os.chmod(INSTANCE_PATH, 0o755)
            print(f"已修改数据库目录权限为755: {INSTANCE_PATH}")
    except Exception as e:
        print(f"修改数据库目录权限失败: {e}")
    
    # 检查数据库文件权限
    if os.path.exists(DB_PATH):
        try:
            db_perms = os.stat(DB_PATH).st_mode & 0o777
            if db_perms != 0o644:
                os.chmod(DB_PATH, 0o644)
                print(f"已修改数据库文件权限为644: {DB_PATH}")
        except Exception as e:
            print(f"修改数据库文件权限失败: {e}")
    
    # 确保日志目录存在
    if not os.path.exists(LOG_PATH):
        os.makedirs(LOG_PATH)
    
    # 确保上传目录存在
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
        # 创建海报目录
        poster_path = os.path.join(UPLOAD_FOLDER, 'posters')
        if not os.path.exists(poster_path):
            os.makedirs(poster_path)
    
    # 确保session目录存在
    if not os.path.exists(SESSION_FILE_DIR):
        os.makedirs(SESSION_FILE_DIR)

# 创建并设置目录权限
ensure_directories()

class Config:
    """应用配置类"""
    # 基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(16)
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)  # 会话持续7天
    
    # 日志配置
    LOG_PATH = LOG_PATH
    LOG_FILE = os.path.join(LOG_PATH, 'cqnu_association.log')
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT', 10))
    LOG_MAX_BYTES = int(os.environ.get('LOG_MAX_BYTES', 10 * 1024 * 1024))  # 10MB
    
    # 上传文件配置
    UPLOAD_FOLDER = UPLOAD_FOLDER
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'docx', 'xlsx', 'pptx', 'txt', 'zip'}
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 默认16MB
    
    # 数据库配置
    INSTANCE_PATH = INSTANCE_PATH
    DB_PATH = DB_PATH
    
    # --- 用下面的代码块替换掉旧的数据库URI设置逻辑 ---
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        raise ValueError("关键错误：环境变量 DATABASE_URL 未设置！请检查你的 .env 文件是否在项目根目录并且内容正确。")
    
    # 兼容 Heroku/Render 的 postgres:// 前缀
    if DATABASE_URL.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    else:
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    # --- 替换结束 ---
    
    # SQLAlchemy配置
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'connect_args': {'check_same_thread': False} if 'sqlite:' in str(SQLALCHEMY_DATABASE_URI) else {},
    }
    
    # 时区配置
    TIMEZONE_NAME = os.environ.get('TIMEZONE_NAME', 'Asia/Shanghai')
    
    # 如果使用PostgreSQL，设置时区
    if 'postgresql:' in str(SQLALCHEMY_DATABASE_URI):
        SQLALCHEMY_ENGINE_OPTIONS['connect_args'] = {
            'options': f'-c timezone=UTC'  # 强制PostgreSQL连接使用UTC时区
        }
    
    # Flask-Session配置
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = SESSION_FILE_DIR
    SESSION_PERMANENT = True
    SESSION_USE_SIGNER = True
    
    # Flask-Cache配置
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get('CACHE_TIMEOUT', 300))
    
    # Flask-Limiter配置
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL', 'memory://')
    RATELIMIT_DEFAULT = os.environ.get('RATELIMIT_DEFAULT', '200 per day, 50 per hour')
    RATELIMIT_STRATEGY = 'fixed-window'
    
    # 系统设置
    APP_NAME = os.environ.get('APP_NAME', '重庆师范大学师能素质协会')
    ITEMS_PER_PAGE = int(os.environ.get('ITEMS_PER_PAGE', 10))
    
    # 活动类型
    ACTIVITY_TYPES = ['cultural', 'sports', 'academic', 'volunteer', 'competition', 'other']
    
    @classmethod
    def init_app(cls, app):
        """初始化应用配置"""
        # 打印时区信息到日志
        app.logger.info(f"使用数据库: {app.config['SQLALCHEMY_DATABASE_URI']}")
        app.logger.info(f"使用时区: {app.config['TIMEZONE_NAME']}")

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    SQLALCHEMY_ECHO = os.environ.get('SQLALCHEMY_ECHO', 'false').lower() == 'true'
    
class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    
class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    TESTING = False
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # 生产环境下的额外配置
        import logging
        from logging.handlers import SMTPHandler
        
        # 获取邮件配置
        mail_server = os.environ.get('MAIL_SERVER')
        mail_port = int(os.environ.get('MAIL_PORT', 25))
        mail_sender = os.environ.get('MAIL_SENDER')
        mail_admin = os.environ.get('MAIL_ADMIN')
        mail_username = os.environ.get('MAIL_USERNAME')
        mail_password = os.environ.get('MAIL_PASSWORD')
        
        # 只有当必要的配置都存在时才添加邮件处理器
        if mail_server and mail_sender and mail_admin:
            # 配置邮件错误日志
            mail_handler = SMTPHandler(
                mailhost=(mail_server, mail_port),
                fromaddr=mail_sender,
                toaddrs=[mail_admin],
                subject='应用错误',
                credentials=(mail_username, mail_password) if mail_username and mail_password else None,
                secure=()
            )
            mail_handler.setLevel(logging.ERROR)
            app.logger.addHandler(mail_handler)

# 根据环境变量选择配置
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    
    'default': DevelopmentConfig
} 