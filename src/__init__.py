import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_caching import Cache
from datetime import datetime
from src.config import Config
from src.utils.time_helpers import display_datetime, get_beijing_time

# 初始化扩展，但不传入app实例
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
cache = Cache()

# 尝试导入Flask-Limiter，如果不存在则使用一个空的占位符
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    limiter = Limiter(key_func=get_remote_address)
except ImportError:
    # 如果Flask-Limiter不可用，创建一个假的Limiter类
    class FakeLimiter:
        def __init__(self, **kwargs):
            pass
        
        def init_app(self, app):
            pass
            
    limiter = FakeLimiter()
    print("警告: Flask-Limiter未安装，速率限制功能将被禁用")

logger = logging.getLogger(__name__)

def create_app(config_name=None):
    app = Flask(__name__)
    
    # 配置应用
    if config_name:
        app.config.from_object(config_name)
    else:
        app.config.from_object(Config)
    
    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    cache.init_app(app)
    limiter.init_app(app)
    
    # 记录环境和时区信息
    with app.app_context():
        app.logger.info(f"应用启动于环境: {os.environ.get('FLASK_ENV', 'development')}")
        app.logger.info(f"数据库URI: {app.config.get('SQLALCHEMY_DATABASE_URI', '未设置')}")
        app.logger.info(f"当前系统时间: {datetime.now()}")
        
        # 设置Render环境变量
        if os.environ.get('RENDER', '') == 'true':
            app.config['IS_RENDER_ENVIRONMENT'] = True
            app.logger.info("检测到Render环境")
        else:
            app.config['IS_RENDER_ENVIRONMENT'] = False
    
    # 注册蓝图
    from src.routes.main import main_bp
    from src.routes.auth import auth_bp
    from src.routes.admin import admin_bp
    from src.routes.student import student_bp
    from src.routes.checkin import checkin_bp
    from src.routes.tag import tag_bp
    from src.routes.errors import errors_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(checkin_bp)
    app.register_blueprint(tag_bp)
    app.register_blueprint(errors_bp)
    
    # 注册错误处理器
    register_error_handlers(app)
    
    # 注册命令
    register_commands(app)
    
    # 添加全局模板函数
    register_template_functions(app)
    
    # 添加全局上下文处理器
    register_context_processors(app)
    
    # 设置日志
    if not app.debug and not app.testing:
        # 确保logs目录存在
        log_dir = os.path.join(app.root_path, 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # 设置文件处理器
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, 'cqnu_association.log'),
            maxBytes=10240,
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        
        # 添加处理器到应用日志和根日志
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('CQNU Association startup')
    
    return app

def register_template_functions(app):
    """注册全局模板函数"""
    try:
        # 导入所有时间处理函数
        from src.utils.time_helpers import (
            display_datetime, format_datetime, localize_time, 
            get_beijing_time, is_render_environment
        )
        
        # 注册基本的时间显示函数
        app.jinja_env.globals.update(display_datetime=display_datetime)
        app.jinja_env.globals.update(format_datetime=format_datetime)
        app.jinja_env.globals.update(localize_time=localize_time)
        app.jinja_env.globals.update(get_beijing_time=get_beijing_time)
        app.jinja_env.globals.update(is_render_environment=is_render_environment)
        
        # 添加一个简单的当前时间函数
        def now_beijing():
            return get_beijing_time()
        app.jinja_env.globals.update(now_beijing=now_beijing)
        
        app.logger.info("已注册时间处理全局模板函数")
    except (ImportError, AttributeError) as e:
        app.logger.error(f"注册时间处理函数失败: {str(e)}")
        
        # 提供备用函数
        def fallback_display_datetime(dt, format_str='%Y-%m-%d %H:%M'):
            if dt is None:
                return ''
            try:
                return dt.strftime(format_str)
            except:
                return str(dt)
        
        def fallback_now():
            return datetime.now()
                
        app.jinja_env.globals.update(display_datetime=fallback_display_datetime)
        app.jinja_env.globals.update(format_datetime=fallback_display_datetime)
        app.jinja_env.globals.update(now_beijing=fallback_now)
        app.logger.info("已注册备用时间处理全局模板函数")

def register_context_processors(app):
    """注册全局上下文处理器，确保所有模板都能访问特定变量"""
    @app.context_processor
    def inject_now_and_helpers():
        return {
            'now': datetime.now(),
            'display_datetime': display_datetime,
            'get_beijing_time': get_beijing_time
        }
    app.logger.info("已注册全局上下文处理器")

def register_error_handlers(app):
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('500.html'), 500

def register_commands(app):
    """注册自定义Flask命令"""
    
    @app.cli.command('init')
    def init():
        """初始化数据库"""
        from src.models import Role, User
        
        db.create_all()
        
        # 创建角色
        if Role.query.count() == 0:
            roles = ['Admin', 'Student']
            for role_name in roles:
                role = Role(name=role_name)
                db.session.add(role)
            db.session.commit()
            print('角色创建成功')
        
        # 创建管理员账户
        if User.query.filter_by(username='admin').first() is None:
            admin_role = Role.query.filter_by(name='Admin').first()
            admin = User(
                username='admin',
                password_hash='pbkdf2:sha256:150000$GJD7cGxS$8f77b1d2be65a1d8a58dac5a1d6c1d6f9c287a20d9c3ce069b4d99a852ce0c1a',  # 默认密码: admin
                role_id=admin_role.id if admin_role else None
            )
            db.session.add(admin)
            db.session.commit()
            print('管理员账户创建成功')
        
        print('初始化完成') 