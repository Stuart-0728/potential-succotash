from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_caching import Cache
from src.config import Config
import logging

logger = logging.getLogger(__name__)

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
cache = Cache()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # 初始化扩展
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    
    # 配置缓存
    cache.init_app(app, config={
        'CACHE_TYPE': 'simple',
        'CACHE_DEFAULT_TIMEOUT': 86400  # 24小时 = 86400秒
    })
    
    # 确保数据库结构完整
    try:
        from scripts.ensure_db_structure import ensure_db_structure
        ensure_db_structure(app, db)
    except Exception as e:
        logger.error(f"确保数据库结构时出错: {e}")
    
    # 注册蓝图
    from src.routes.main import main_bp
    from src.routes.auth import auth_bp
    from src.routes.admin import admin_bp
    from src.routes.student import student_bp
    from src.routes.checkin import checkin_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(checkin_bp)
    
    return app 