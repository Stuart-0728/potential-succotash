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