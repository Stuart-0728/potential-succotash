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
        beijing_tz = pytz.timezone('Asia/Shanghai')
        return datetime.datetime.now(beijing_tz)
    except RuntimeError:  # 如果不在应用上下文中
        return datetime.datetime.now(pytz.timezone('Asia/Shanghai')) 

def convert_to_utc(dt):
    """
    将一个时间转换为UTC时间
    :param dt: 需要转换的datetime对象
    :return: UTC时间
    """
    if dt is None:
        return None
    
    # 如果dt已经有时区，则直接转换为UTC
    if dt.tzinfo is not None:
        return dt.astimezone(pytz.utc)
    
    # 如果dt没有时区，假设它是北京时间，然后转换为UTC
    beijing_tz = pytz.timezone('Asia/Shanghai')
    localized_dt = beijing_tz.localize(dt)
    return localized_dt.astimezone(pytz.utc)

def format_datetime(dt, format_str='%Y-%m-%d %H:%M'):
    """
    格式化时间为指定格式的字符串
    :param dt: 需要格式化的datetime对象
    :param format_str: 格式化字符串
    :return: 格式化后的字符串
    """
    if dt is None:
        return ''
    
    # 确保时间是北京时间
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt).astimezone(pytz.timezone('Asia/Shanghai'))
    elif dt.tzinfo != pytz.timezone('Asia/Shanghai'):
        dt = dt.astimezone(pytz.timezone('Asia/Shanghai'))
        
    return dt.strftime(format_str)

def is_naive_datetime(dt):
    """
    检查一个datetime对象是否是naive的（没有时区信息）
    :param dt: datetime对象
    :return: 如果是naive的返回True，否则返回False
    """
    return dt.tzinfo is None

def ensure_timezone_aware(dt, default_timezone='Asia/Shanghai'):
    """
    确保datetime对象有时区信息，如果没有则添加默认时区
    :param dt: datetime对象
    :param default_timezone: 默认时区名称
    :return: 带有时区信息的datetime对象
    """
    if dt is None:
        return None
        
    if is_naive_datetime(dt):
        tz = pytz.timezone(default_timezone)
        return tz.localize(dt)
    return dt

def compare_datetimes(dt1, dt2):
    """
    安全地比较两个datetime对象，确保它们都有时区信息
    :param dt1: 第一个datetime对象
    :param dt2: 第二个datetime对象
    :return: dt1 < dt2返回-1，dt1 == dt2返回0，dt1 > dt2返回1
    """
    if dt1 is None and dt2 is None:
        return 0
    if dt1 is None:
        return -1
    if dt2 is None:
        return 1
        
    # 确保两个时间都有时区信息
    dt1 = ensure_timezone_aware(dt1)
    dt2 = ensure_timezone_aware(dt2)
    
    # 由于已经检查了None值，这里可以安全地使用时间戳比较
    try:
        ts1 = dt1.timestamp()
        ts2 = dt2.timestamp()
        
        if ts1 < ts2:
            return -1
        elif ts1 > ts2:
            return 1
        else:
            return 0
    except (AttributeError, TypeError):
        # 如果出现错误，回退到字符串比较
        str1 = str(dt1)
        str2 = str(dt2)
        if str1 < str2:
            return -1
        elif str1 > str2:
            return 1
        else:
            return 0 