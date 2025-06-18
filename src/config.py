import os
import pytz

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///../instance/cqnu_association.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300
    # 设置时区为北京时间
    TIMEZONE = pytz.timezone('Asia/Shanghai')
    # 添加时区名称，方便在模板中使用
    TIMEZONE_NAME = 'Asia/Shanghai'
    # 确保SQLAlchemy使用UTC时间
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {'timezone': '+08:00'}
    } 