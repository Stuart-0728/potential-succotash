import os
import sys
import logging
from werkzeug.security import generate_password_hash

# Add the project root directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def reset_admin_password():
    """重置管理员用户密码"""
    try:
        # Import from the application
        from src import create_app, db
        from src.models import User
        
        # Create a Flask app to get the database context
        app = create_app()
        
        with app.app_context():
            # Specify the username and new password
            username = 'stuart'
            new_password = 'LYXspassword123'
            
            print(f"正在为用户 '{username}' 重置密码...")
            
            # Find the user using SQLAlchemy 2.0 style query
            stmt = db.select(User).filter_by(username=username)
            user = db.session.execute(stmt).scalar_one_or_none()
            
            if not user:
                print(f"错误: 用户 '{username}' 不存在")
                
                # Try to list all users
                users_stmt = db.select(User)
                users = db.session.execute(users_stmt).scalars().all()
                
                if users:
                    print("\n可用的用户名:")
                    for u in users:
                        print(f" - {u.username}")
                else:
                    print("数据库中没有任何用户。")
                return
            
            # Update the password
            user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            
            logger.info(f"用户 '{username}' 密码重置成功")
            print(f"成功! 用户 '{username}' 的密码已被重置为 '{new_password}'")
            print("请使用此新密码登录，并尽快在个人中心修改它。")
        
    except Exception as e:
        logger.error(f"重置密码出错: {str(e)}")
        print(f"错误: {str(e)}")
        print("请确保你已经激活了虚拟环境，并且数据库配置正确。")

if __name__ == '__main__':
    reset_admin_password() 