import datetime
import pytz
from flask import current_app

def get_beijing_time():
    """
    获取北京时间
    :return: 当前的北京时间，已本地化的datetime对象
    """
    utc_now = datetime.datetime.now(pytz.utc)
    beijing_tz = pytz.timezone('Asia/Shanghai')
    return utc_now.astimezone(beijing_tz)

def localize_time(dt):
    """
    将一个非时区时间转换为北京时间
    :param dt: 需要本地化的datetime对象
    :return: 本地化后的datetime对象
    """
    if dt is None:
        return None
        
    # 如果dt已经有时区，则直接转换
    if dt.tzinfo is not None:
        beijing_tz = pytz.timezone('Asia/Shanghai')
        return dt.astimezone(beijing_tz)
    
    # 如果dt没有时区，假设它是UTC时间，然后转换
    utc_dt = pytz.utc.localize(dt)
    beijing_tz = pytz.timezone('Asia/Shanghai')
    return utc_dt.astimezone(beijing_tz)

def get_localized_now():
    """
    获取本地化的当前时间（北京时间）
    此函数适用于需要与数据库比较时间的情况
    """
    try:
        beijing_tz = current_app.config.get('TIMEZONE', pytz.timezone('Asia/Shanghai'))
        return datetime.datetime.now(beijing_tz)
    except RuntimeError:  # 如果不在应用上下文中
        return datetime.datetime.now(pytz.timezone('Asia/Shanghai')) 