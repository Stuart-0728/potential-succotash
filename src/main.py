import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # DON'T CHANGE THIS !!!

from flask import Flask, render_template, redirect, url_for, flash, request, send_file, Response
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from flask_migrate import Migrate
from src.models import db, User, Role, StudentInfo, Activity, Registration, Announcement, SystemLog
from src.routes.auth import auth_bp
from src.routes.admin import admin_bp
from src.routes.student import student_bp
from src.routes.main import main_bp
from src.routes.utils import utils_bp
import logging
from datetime import datetime
import os

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'cqnu-association-secret-key')

# 根据环境变量决定使用哪种数据库
if os.environ.get('DATABASE_URL'):
    # 生产环境使用环境变量中的数据库URL
    database_url = os.environ.get('DATABASE_URL')
    # 如果是PostgreSQL URL，确保格式正确并添加SSL参数
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    # 为PostgreSQL连接添加SSL参数和连接稳定性配置
    if 'postgresql://' in database_url:
        # 添加所有必要的连接参数
        params = []
        
        # 检查现有参数
        if '?' in database_url:
            base_url, existing_params = database_url.split('?', 1)
            params.extend(existing_params.split('&'))
        else:
            base_url = database_url
        
        # 添加缺失的参数
        param_dict = {p.split('=')[0]: p.split('=')[1] for p in params if '=' in p}
        
        if 'sslmode' not in param_dict:
            params.append('sslmode=require')
        if 'connect_timeout' not in param_dict:
            params.append('connect_timeout=10')
        if 'keepalives' not in param_dict:
            params.append('keepalives=1')
        if 'keepalives_idle' not in param_dict:
            params.append('keepalives_idle=5')
        if 'keepalives_interval' not in param_dict:
            params.append('keepalives_interval=2')
        if 'application_name' not in param_dict:
            params.append('application_name=cqnu_association')
            
        # 重建连接字符串
        database_url = f"{base_url}?{'&'.join(params)}"
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,  # 自动检测断开的连接
        'pool_recycle': 280,    # 连接回收时间（秒）
        'pool_timeout': 30,     # 连接超时时间（秒）
        'max_overflow': 15      # 连接池溢出的最大连接数
    }
    logger.info(f"Using database connection: {database_url.split('@')[0]}@**** with enhanced stability")
else:
    # 本地开发使用SQLite
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cqnu_association.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化数据库
db.init_app(app)
migrate = Migrate(app, db)

# 初始化登录管理器
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'  # 修正为使用'auth.login'而非'login'
login_manager.login_message = '请先登录以访问此页面'

@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except Exception as e:
        logger.error(f"Error loading user: {e}")
        return None

# 注册蓝图 - 修改auth_bp注册方式，不使用url_prefix
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(student_bp)
app.register_blueprint(main_bp)
app.register_blueprint(utils_bp)

# 记录用户最后登录时间
@app.before_request
def before_request():
    try:
        if current_user.is_authenticated:
            current_user.last_login = datetime.now()
            db.session.commit()
    except Exception as e:
        logger.error(f"Error updating last login: {e}")
        db.session.rollback()

# 全局错误处理
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    logger.error(f"500 error: {e}")
    return render_template('500.html'), 500

# 添加全局上下文处理器
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

# 初始化数据库和创建管理员账户
def initialize_database():
    try:
        with app.app_context():
            db.create_all()
            
            # 创建角色
            admin_role = Role.query.filter_by(name='Admin').first()
            if not admin_role:
                admin_role = Role(name='Admin')
                db.session.add(admin_role)
            
            student_role = Role.query.filter_by(name='Student').first()
            if not student_role:
                student_role = Role(name='Student')
                db.session.add(student_role)
            
            # 创建管理员账户
            from werkzeug.security import generate_password_hash
            admin = User.query.filter_by(username='stuart').first()
            if not admin:
                admin = User(
                    username='stuart',
                    email='admin@cqnu.edu.cn',
                    password_hash=generate_password_hash('LYXspassword123'),
                    role_id=admin_role.id
                )
                db.session.add(admin)
            
            # 创建示例活动
            if Activity.query.count() == 0:
                activities = [
                    Activity(
                        title='教学技能培训工作坊',
                        description='本次工作坊将邀请教育专家分享现代教学方法和技巧，帮助师范生提升教学能力。内容包括课堂管理、教学设计、多媒体教学等方面。参与者将有机会进行实践演练，获得专家点评和指导。',
                        location='教学楼A栋201',
                        start_time=datetime(2025, 6, 15, 14, 0),
                        end_time=datetime(2025, 6, 15, 17, 0),
                        registration_deadline=datetime(2025, 6, 10, 23, 59),
                        max_participants=50,
                        created_by=1,
                        status='active'
                    ),
                    Activity(
                        title='教育实习经验分享会',
                        description='邀请已完成教育实习的高年级学生分享实习经验和心得，帮助即将实习的同学做好准备。分享内容包括实习学校选择、课堂管理技巧、与指导教师沟通方法、教案准备等实用信息，以及应对各种挑战的策略。',
                        location='图书馆报告厅',
                        start_time=datetime(2025, 6, 20, 19, 0),
                        end_time=datetime(2025, 6, 20, 21, 0),
                        registration_deadline=datetime(2025, 6, 18, 23, 59),
                        max_participants=100,
                        created_by=1,
                        status='active'
                    )
                ]
                for activity in activities:
                    db.session.add(activity)
            
            db.session.commit()
            logger.info("Database initialized successfully")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error initializing database: {e}")

# 在应用启动时初始化数据库
with app.app_context():
    initialize_database()

# 添加一个路由来处理"关于我们"页面
@app.route('/about')
def about():
    return render_template('main/about.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
