import os
import logging
from logging.handlers import RotatingFileHandler
import pytz
from flask import Flask, session, g
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_session import Session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from datetime import datetime
from src.config import Config

# 创建SQLAlchemy实例
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
sess = Session()
limiter = Limiter(key_func=get_remote_address)
cache = Cache()

# 尝试导入Flask-Limiter，如果不可用则创建一个空对象
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    limiter = Limiter(key_func=get_remote_address)
except ImportError:
    # 创建一个模拟对象，避免错误
    class MockLimiter:
        def __init__(self, *args, **kwargs):
            pass
            
        def init_app(self, app):
            app.logger.warning("Flask-Limiter未安装，速率限制功能将被禁用")
            
        def limit(self, *args, **kwargs):
            def decorator(f):
                return f
            return decorator
    
    limiter = MockLimiter()

logger = logging.getLogger(__name__)

def create_app(config_name=None):
    """创建Flask应用"""
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')
    
    app = Flask(__name__, instance_relative_config=True)
    
    # 从config.py导入配置
    from .config import config
    app.config.from_object(config[config_name])
    
    # 必须显式调用init_app方法以确保权限设置等自定义初始化
    config[config_name].init_app(app)
    
    # 配置日志
    setup_logging(app)
    
    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    sess.init_app(app)
    limiter.init_app(app)
    cache.init_app(app)
    
    # 配置登录管理器
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录以访问此页面'
    login_manager.login_message_category = 'info'
    
    # 初始化模型 - 在应用上下文中进行，确保db已经初始化
    with app.app_context():
        # 导入所有模型
        from src.models import User, StudentInfo, Activity, Registration, Tag, Role
        from src.models import PointsHistory, ActivityReview, Announcement, SystemLog
        from src.models import ActivityCheckin, Message, Notification, NotificationRead
        from src.models import AIChatHistory, AIChatSession, AIUserPreferences
        
        # 确保模型与当前app关联
        db.create_all()
        
        # 设置用户加载函数
        @login_manager.user_loader
        def load_user(user_id):
            """加载用户信息，供Flask-Login使用"""
            return User.query.get(int(user_id))
    
    # 注册蓝图 - 在模型初始化之后
    register_blueprints(app)
    
    # 注册时区处理中间件
    @app.before_request
    def before_request():
        """在请求处理前设置时区"""
        timezone_name = app.config.get('TIMEZONE_NAME', 'Asia/Shanghai')
        # 将时区存储在会话中，方便在模板和视图中使用
        session['timezone'] = timezone_name
        g.timezone = pytz.timezone(timezone_name)
    
    # 注册Shell上下文
    @app.shell_context_processor
    def make_shell_context():
        """为Flask shell提供上下文"""
        # 延迟导入模型，避免循环导入
        from src.models import User, Activity, Registration, Tag
        return dict(
            app=app, db=db, 
            User=User, Activity=Activity, 
            Registration=Registration,
            Tag=Tag
        )
    
    # 错误处理
    register_error_handlers(app)
    
    # 命令行命令
    register_commands(app)
    
    # 确保数据库目录和文件有正确的权限
    with app.app_context():
        if 'sqlite:' in str(app.config['SQLALCHEMY_DATABASE_URI']):
            db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
            db_dir = os.path.dirname(db_path)
            
            # 确保目录存在且有正确权限
            if not os.path.exists(db_dir):
                try:
                    os.makedirs(db_dir, mode=0o755)
                    app.logger.info(f"已创建数据库目录: {db_dir}")
                except Exception as e:
                    app.logger.error(f"创建数据库目录失败: {e}")
            
            # 设置目录权限
            try:
                os.chmod(db_dir, 0o755)
                app.logger.info(f"已设置数据库目录权限: {db_dir}")
            except Exception as e:
                app.logger.error(f"设置数据库目录权限失败: {e}")
            
            # 设置数据库文件权限
            if os.path.exists(db_path):
                try:
                    os.chmod(db_path, 0o644)
                    app.logger.info(f"已设置数据库文件权限: {db_path}")
                except Exception as e:
                    app.logger.error(f"设置数据库文件权限失败: {e}")
    
    # 注册模板函数
    register_template_functions(app)
    
    # 注册全局上下文处理器
    register_context_processors(app)
    
    # 调用确保数据库结构的脚本
    with app.app_context():
        try:
            from scripts.ensure_db_structure import ensure_db_structure
            ensure_db_structure()
        except ImportError:
            app.logger.warning("未找到确保数据库结构的脚本，跳过初始化")
        except Exception as e:
            app.logger.error(f"初始化数据库结构时出错: {e}")
    
    return app

def setup_logging(app):
    """配置日志系统"""
    log_dir = app.config.get('LOG_FOLDER')
    if log_dir is None:
        log_dir = os.path.join(app.root_path, 'logs')
        app.logger.warning(f"未配置LOG_FOLDER，使用默认日志目录: {log_dir}")
        
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, mode=0o755)
    
    log_file = os.path.join(log_dir, app.config.get('LOG_FILENAME', 'cqnu_association.log'))
    
    # 配置根日志记录器
    log_level_name = app.config.get('LOG_LEVEL', 'INFO')
    if isinstance(log_level_name, str):
        log_level = getattr(logging, log_level_name)
    else:
        log_level = logging.INFO
        app.logger.warning(f"LOG_LEVEL不是字符串，使用默认INFO级别")
    
    # 创建处理器
    log_format = app.config.get('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=10)
    file_handler.setFormatter(logging.Formatter(log_format))
    file_handler.setLevel(log_level)
    
    # 添加到根日志记录器
    logging.getLogger().setLevel(log_level)
    logging.getLogger().addHandler(file_handler)
    
    # 添加到应用日志记录器
    app.logger.addHandler(file_handler)
    
    # 设置SQLAlchemy日志级别
    if app.config.get('SQLALCHEMY_ECHO'):
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
    
    app.logger.info('日志系统初始化完成')

def register_blueprints(app):
    """注册所有蓝图"""
    # 导入蓝图
    from .routes.main import main_bp
    from .routes.auth import auth_bp
    from .routes.admin import admin_bp
    from .routes.student import student_bp
    from .routes.utils import utils_bp
    from .routes.tag import tag_bp
    from .routes.checkin import checkin_bp
    
    # 注册蓝图
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(utils_bp, url_prefix='/utils')
    app.register_blueprint(tag_bp, url_prefix='/tag')
    app.register_blueprint(checkin_bp, url_prefix='/checkin')
    
    # 注册错误处理蓝图
    from .routes.errors import errors_bp
    app.register_blueprint(errors_bp)

def register_error_handlers(app):
    """注册错误处理函数"""
    from .routes.errors import page_not_found, internal_server_error
    
    app.register_error_handler(404, page_not_found)
    app.register_error_handler(500, internal_server_error)

def register_commands(app):
    """注册Flask命令行命令"""
    @app.cli.command('create-admin')
    def create_admin():
        """创建管理员账户"""
        from .models import User
        from werkzeug.security import generate_password_hash
        
        username = app.config.get('ADMIN_USERNAME', 'admin')
        password = app.config.get('ADMIN_PASSWORD', 'admin')
        
        # 检查管理员是否已存在
        admin = User.query.filter_by(username=username).first()
        if admin:
            print(f'管理员 {username} 已经存在')
            return
        
        # 创建管理员
        admin = User(
            username=username,
            password_hash=generate_password_hash(password),
            is_admin=True,
            is_active=True,
            real_name='管理员',
            student_id='admin',
            email='admin@example.com'
        )
        
        db.session.add(admin)
        db.session.commit()
        
        print(f'已创建管理员账户: {username}')
    
    @app.cli.command('initialize-db')
    def initialize_db():
        """初始化数据库"""
        db.create_all()
        print('数据库初始化完成')

def register_template_functions(app):
    """注册全局模板函数"""
    try:
        # 导入时间处理函数
        from src.utils.time_helpers import display_datetime, get_beijing_time, format_datetime, safe_less_than, safe_greater_than, safe_compare
        
        # 注册时间处理全局模板函数
        app.jinja_env.globals['display_datetime'] = display_datetime
        app.jinja_env.globals['format_datetime'] = format_datetime
        app.jinja_env.globals['get_beijing_time'] = get_beijing_time
        # 添加安全时间比较函数
        app.jinja_env.globals['safe_less_than'] = safe_less_than
        app.jinja_env.globals['safe_greater_than'] = safe_greater_than
        app.jinja_env.globals['safe_compare'] = safe_compare
        logger.info("已注册时间处理全局模板函数")
        
    except Exception as e:
        app.logger.error(f"注册模板函数时出错: {e}")
        
        # 注册一些备用函数，以防时间处理模块出错
        def fallback_display_datetime(dt, format_str='%Y-%m-%d %H:%M'):
            if dt is None:
                return ""
            if isinstance(dt, str):
                return dt
            return dt.strftime(format_str)
        
        def fallback_now():
            return datetime.now()
        
        app.jinja_env.globals.update(display_datetime=fallback_display_datetime)
        app.jinja_env.globals.update(now_beijing=fallback_now)
        app.logger.warning("已注册备用时间处理函数")

def register_context_processors(app):
    """注册全局上下文处理器"""
    @app.context_processor
    def inject_now_and_helpers():
        """注入当前时间和帮助函数到所有模板"""
        # 导入时间处理函数
        from src.utils.time_helpers import display_datetime
        return {
            'now': datetime.now(),
            'display_datetime': display_datetime
        } 