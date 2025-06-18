from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from src.config import Config

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # 初始化扩展
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    
    # 注册蓝图
    from src.routes.main import main_bp
    from src.routes.auth import auth_bp
    from src.routes.admin import admin_bp
    from src.routes.student import student_bp
    from src.routes.checkin import checkin_bp
    from src.routes.select_tags_route import select_tags_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(checkin_bp)
    app.register_blueprint(select_tags_bp)
    
    return app 