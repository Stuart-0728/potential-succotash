import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
import pytz
from datetime import datetime
from flask_caching import Cache
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from src.config import Config
from src.utils.time_helpers import display_datetime

logger = logging.getLogger(__name__)

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
cache = Cache()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)

def create_app(config_name=None):
    app = Flask(__name__)

    # 加载配置
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    # 如果在Render平台上运行，使用生产配置
    if os.environ.get('RENDER') or os.environ.get('IS_RENDER'):
        config_name = 'production'
        os.environ['FLASK_ENV'] = 'production'
    
    from .config import config
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    
    # 记录环境和时区信息
    app.logger.info(f"应用启动在 {config_name} 环境")
    app.logger.info(f"当前UTC时间: {datetime.utcnow()}")
    app.logger.info(f"配置的时区: {app.config.get('TIMEZONE', 'UTC')}")
    beijing_time = datetime.now(pytz.timezone('Asia/Shanghai'))
    app.logger.info(f"当前北京时间: {beijing_time}")
    
    # 配置时区检测
    @app.before_request
    def setup_timezone():
        # 在全局变量中存储当前本地化的北京时间
        app.config['current_beijing_time'] = datetime.now(pytz.timezone('Asia/Shanghai'))
        
        # 检测是否在Render环境
        if app.config.get('IS_RENDER_ENVIRONMENT', False):
            app.logger.debug("在Render环境中运行，时间为UTC")
        else:
            app.logger.debug("在本地环境中运行，时间为本地时区")
    
    # 模板全局变量
    @app.context_processor
    def inject_timezone_data():
        """注入时区相关的变量到模板"""
        def get_current_beijing_time():
            """获取当前的北京时间"""
            return datetime.now(pytz.timezone('Asia/Shanghai'))
        
        return {
            'get_current_beijing_time': get_current_beijing_time,
            'timezone_name': app.config.get('TIMEZONE', 'Asia/Shanghai')
        }
    
    # 注册蓝图
    from .routes.main import main_bp
    from .routes.auth import auth_bp
    from .routes.admin import admin_bp
    from .routes.student import student_bp
    from .routes.utils import utils_bp
    from .routes.tag import tag_bp
    from .routes.checkin import checkin_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(utils_bp)
    app.register_blueprint(tag_bp, url_prefix='/tags')
    app.register_blueprint(checkin_bp, url_prefix='/checkin')

    # 错误处理
    from .routes.errors import register_error_handlers
    register_error_handlers(app)
    
    # 注册用户加载函数
    from .models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # 全局处理函数
    @app.context_processor
    def inject_utils():
        from .utils.time_helpers import format_datetime
        
        return dict(
            format_datetime=format_datetime,
        )
    
    # 注册命令
    register_commands(app)

    # 添加全局模板函数
    app.jinja_env.globals.update(display_datetime=display_datetime)
    
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

def register_commands(app):
    """注册自定义命令"""
    
    @app.cli.command('create-admin')
    def create_admin():
        """创建一个管理员用户"""
        from .models import User, Role
        from werkzeug.security import generate_password_hash
        
        # 检查是否已有管理员
        admin_exists = User.query.filter_by(role_id=Role.ADMIN).first()
        if admin_exists:
            print('管理员用户已存在')
            return
        
        # 创建管理员用户
        username = input('请输入管理员用户名: ')
        password = input('请输入管理员密码: ')
        
        admin = User(username=username, password_hash=generate_password_hash(password), role_id=Role.ADMIN)
        try:
            db.session.add(admin)
            db.session.commit()
            print(f'管理员用户 {username} 创建成功')
        except Exception as e:
            db.session.rollback()
            print(f'创建管理员失败: {str(e)}')
    
    @app.cli.command('reset-db')
    def reset_db():
        """重置数据库 (仅开发环境使用)"""
        if app.config['ENV'] != 'development':
            print('此命令仅在开发环境可用')
            return
            
        if input('确定要重置数据库? 所有数据将被删除! (y/n): ').lower() == 'y':
            try:
                db.drop_all()
                db.create_all()
                print('数据库已重置')
            except Exception as e:
                print(f'重置数据库失败: {str(e)}')
        else:
            print('已取消操作') 