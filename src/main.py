import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # DON'T CHANGE THIS !!!

from flask import Flask, render_template, redirect, url_for, flash, request, send_file, Response
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from flask_migrate import Migrate
from src.models import db, User, Role, StudentInfo, Activity, Registration, Announcement, SystemLog, Tag
from src.routes.auth import auth_bp
from src.routes.admin import admin_bp
from src.routes.student import student_bp
from src.routes.main import main_bp
from src.routes.utils import utils_bp
from src.routes.tag import tag_bp
from src.routes.checkin import checkin_bp
import logging
from datetime import datetime
import os
from werkzeug.security import generate_password_hash
import pytz
from src.utils.time_helpers import get_beijing_time
from sqlalchemy import inspect, text

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 确保上传文件夹存在
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads', 'posters')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER  # 设置上传文件夹路径

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

# 确保数据库表存在
with app.app_context():
    try:
        # 使用ensure_db_structure函数确保数据库结构完整
        from scripts.ensure_db_structure import ensure_db_structure
        ensure_db_structure(app, db)
        
        # 检查是否需要创建默认角色
        if Role.query.count() == 0:
            admin_role = Role(name='Admin', description='管理员')
            student_role = Role(name='Student', description='学生')
            db.session.add(admin_role)
            db.session.add(student_role)
            db.session.commit()
            logger.info("默认角色已创建")
            
        # 检查是否需要创建默认标签
        if Tag.query.count() == 0:
            default_tags = [
                {'name': '讲座', 'color': 'primary', 'description': '各类学术讲座'},
                {'name': '实践', 'color': 'success', 'description': '实践活动'},
                {'name': '竞赛', 'color': 'danger', 'description': '各类比赛'},
                {'name': '文艺', 'color': 'info', 'description': '文艺活动'},
                {'name': '体育', 'color': 'warning', 'description': '体育活动'},
                {'name': '志愿', 'color': 'secondary', 'description': '志愿服务'},
            ]
            for tag_info in default_tags:
                tag = Tag(**tag_info)
                db.session.add(tag)
            db.session.commit()
            logger.info("默认标签已创建")
            
        # 自动创建初始管理员账号
        if User.query.filter_by(username='stuart').first() is None:
            admin_role = Role.query.filter(Role.name == 'Admin').first()
            if not admin_role:
                admin_role = Role(name='Admin', description='管理员')
                db.session.add(admin_role)
                db.session.commit()
            user = User(
                username='stuart',
                email='admin@cqnu.edu.cn',
                password_hash=generate_password_hash('LYXspassword123'),
                role=admin_role
            )
            db.session.add(user)
            db.session.commit()
            logger.info("初始管理员账号已创建：stuart / LYXspassword123")
    except Exception as e:
        logger.error(f"数据库初始化错误: {str(e)}")

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
app.register_blueprint(tag_bp, url_prefix='/tag')
app.register_blueprint(checkin_bp, url_prefix='/checkin')

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
    return {'now': get_beijing_time()}

# 初始化数据库和创建管理员账户
def initialize_database():
    try:
        with app.app_context():
            db.drop_all()  # 重置数据库
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
                    role=admin_role
                )
                db.session.add(admin)
            # --- 自动修正 stuart 账号角色指向 ---
            stuart = User.query.filter_by(username='stuart').first()
            admin_role = Role.query.filter_by(name='Admin').first()
            if stuart and admin_role and stuart.role_id != admin_role.id:
                stuart.role_id = admin_role.id
                db.session.commit()
                logger.info("已自动修正 stuart 账号的角色指向 Admin")
            # --- END ---
            # 初始化部分标签
            tag_names = ['学术', '文体', '志愿', '创新', '竞赛', '讲座', '社会实践']
            for name in tag_names:
                if not Tag.query.filter_by(name=name).first():
                    db.session.add(Tag(name=name))
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
# with app.app_context():
#     initialize_database()

# 添加一个路由来处理"关于我们"页面
@app.route('/about')
def about():
    return render_template('main/about.html')

def create_app():
    app = Flask(__name__)
    
    # 配置数据库连接
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        
        # 添加 SSL 参数
        if 'postgresql://' in database_url and '?' not in database_url:
            database_url += '?sslmode=require'
        
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cqnu_association.db'
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key')
    
    # 初始化扩展
    db.init_app(app)
    login_manager.init_app(app)
    
    # 注册蓝图
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(main_bp)
    
    return app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
