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
from src.config import config, Config

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
        # 初始化数据库模型
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
            return db.session.get(User, int(user_id))
    
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
            # 注释掉以下两行，因为它们是为本地SQLite设计的，在连接PostgreSQL时会引发问题
            # from scripts.ensure_db_structure import ensure_db_structure
            # ensure_db_structure()
            app.logger.info("已跳过SQLite数据库结构检查，因为当前使用PostgreSQL数据库")
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
    from .routes.education import education_bp
    
    # 注册蓝图
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(utils_bp, url_prefix='/utils')
    app.register_blueprint(tag_bp, url_prefix='/tag')
    app.register_blueprint(checkin_bp, url_prefix='/checkin')
    app.register_blueprint(education_bp, url_prefix='/education')
    
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
        from src.models import User, Role
        from werkzeug.security import generate_password_hash
        
        # 检查是否已存在管理员角色
        admin_role = db.session.execute(db.select(Role).filter_by(name='Admin')).scalar_one_or_none()
        if admin_role is None:
            admin_role = Role(name='Admin', description='管理员')
            db.session.add(admin_role)
            db.session.commit()
            app.logger.info('已创建管理员角色')
        
        # 创建管理员用户
        admin = db.session.execute(db.select(User).filter_by(username='admin')).scalar_one_or_none()
        if admin is None:
            admin = User(
                username='admin',
                email='admin@example.com',
                password_hash=generate_password_hash('admin123'),
                role_id=admin_role.id
            )
            db.session.add(admin)
            db.session.commit()
            app.logger.info('已创建管理员用户: admin/admin123')
        else:
            app.logger.info('管理员用户已存在')
    
    @app.cli.command('initialize-db')
    def initialize_db():
        """初始化数据库"""
        db.create_all()
        app.logger.info('已初始化数据库表')

def register_template_functions(app):
    """注册模板函数"""
    # 从utils.time_helpers导入时间处理函数
    from src.utils.time_helpers import display_datetime, format_datetime, get_beijing_time
    
    # 注册时间处理函数
    @app.template_filter('datetime')
    def _display_datetime(dt, fmt=None):
        """格式化日期时间，考虑时区转换"""
        return display_datetime(dt, fmt=fmt)
    
    @app.template_filter('format_date')
    def _format_date(dt):
        """格式化为日期"""
        return display_datetime(dt, fmt='%Y-%m-%d')
    
    @app.template_filter('format_time')
    def _format_time(dt):
        """格式化为时间"""
        return display_datetime(dt, fmt='%H:%M:%S')
    
    @app.template_filter('format_datetime')
    def _format_datetime(dt, fmt='%Y-%m-%d %H:%M'):
        """简单格式化日期时间，不考虑时区转换"""
        return format_datetime(dt, fmt)
    
    @app.template_global('now')
    def _now():
        """获取当前北京时间"""
        return get_beijing_time()
    
    app.logger.info('已注册时间处理全局模板函数')

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