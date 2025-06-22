import datetime
import pytz
from flask import current_app

def get_beijing_time():
    """
    获取北京时间
    :return: 当前的北京时间，已本地化的datetime对象
    """
    beijing_tz = pytz.timezone('Asia/Shanghai')
    # 使用utcnow()获取UTC时间，然后转换为北京时间
    # 这样可以避免服务器时区设置的影响
    utc_now = datetime.datetime.utcnow()
    utc_now = pytz.utc.localize(utc_now)
    return utc_now.astimezone(beijing_tz)

def is_render_environment():
    """
    检查当前是否在Render环境中运行
    :return: 如果在Render环境中返回True，否则返回False
    """
    import os
    return os.environ.get('RENDER', '') == 'true'

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
    获取当前时间，统一使用UTC时间
    此函数适用于需要与数据库比较时间的情况
    """
    # 统一返回UTC时间，不再区分环境
    return datetime.datetime.utcnow()

def convert_to_utc(dt):
    """
    将一个时间转换为UTC时间
    :param dt: 需要转换的datetime对象
    :return: UTC时间（无时区信息）
    """
    if dt is None:
        return None
    
    # 如果dt已经有时区，则直接转换为UTC
    if dt.tzinfo is not None:
        return dt.astimezone(pytz.utc).replace(tzinfo=None)
    
    # 如果dt没有时区，并且在Render环境下，假设它已经是UTC时间
    if is_render_environment():
        return dt
    
    # 如果在本地环境，则假设它是北京时间，需要转为UTC
    beijing_tz = pytz.timezone('Asia/Shanghai')
    localized_dt = beijing_tz.localize(dt)
    return localized_dt.astimezone(pytz.utc).replace(tzinfo=None)

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
    beijing_time = dt
    if dt.tzinfo is None:
        # 如果没有时区信息，假设它是UTC时间，转换为北京时间
        if is_render_environment():
            beijing_time = pytz.utc.localize(dt).astimezone(pytz.timezone('Asia/Shanghai'))
        else:
            # 本地环境，假设已经是北京时间
            beijing_time = pytz.timezone('Asia/Shanghai').localize(dt)
    elif dt.tzinfo != pytz.timezone('Asia/Shanghai'):
        # 如果有时区信息但不是北京时间，转换为北京时间
        beijing_time = dt.astimezone(pytz.timezone('Asia/Shanghai'))
        
    return beijing_time.strftime(format_str)

def is_naive_datetime(dt):
    """
    检查一个datetime对象是否没有时区信息
    :param dt: datetime对象
    :return: 如果没有时区信息，返回True；否则返回False
    """
    return dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None

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
        # 统一处理：所有没有时区的时间都按照默认时区处理
        tz = pytz.timezone(default_timezone)
        return tz.localize(dt)
    return dt

def normalize_datetime_for_db(dt):
    """
    规范化datetime对象，以便存储到数据库中
    统一存储为UTC时间（无时区信息）
    :param dt: datetime对象
    :return: 规范化后的datetime对象（UTC时间，无时区信息）
    """
    if dt is None:
        return None
    
    # 确保时间有时区信息
    aware_dt = ensure_timezone_aware(dt)
    
    # 转换为UTC并去除时区信息
    if aware_dt is not None:
        utc_dt = aware_dt.astimezone(pytz.utc).replace(tzinfo=None)
        return utc_dt
    return None

def display_datetime(dt, format_str='%Y-%m-%d %H:%M'):
    """
    将数据库中的时间转换为显示时间（北京时间）
    :param dt: 数据库中的datetime对象（UTC时间，无时区信息）
    :param format_str: 格式化字符串
    :return: 格式化后的字符串
    """
    if dt is None:
        return ''
        
    if not isinstance(dt, datetime.datetime):
        return str(dt)
    
    try:
        # 假设数据库中的时间是UTC时间（无时区信息）
        if dt.tzinfo is None:
            utc_dt = pytz.utc.localize(dt)
        else:
            utc_dt = dt.astimezone(pytz.utc)
        
        # 转换为北京时间
        beijing_dt = utc_dt.astimezone(pytz.timezone('Asia/Shanghai'))
        
        # 格式化并返回
        return beijing_dt.strftime(format_str)
    except Exception as e:
        # 如果出现任何错误，尝试直接格式化
        try:
            return dt.strftime(format_str)
        except:
            return str(dt)

def safe_compare(dt1, dt2):
    """
    安全比较两个日期时间，处理时区问题
    :param dt1: 第一个datetime对象
    :param dt2: 第二个datetime对象
    :return: 比较结果 (True/False)
    """
    # 确保两个时间都是timezone aware的
    dt1_aware = ensure_timezone_aware(dt1) if dt1 else None
    dt2_aware = ensure_timezone_aware(dt2) if dt2 else None
    
    # 如果任一为None，则无法比较
    if dt1_aware is None or dt2_aware is None:
        return False
    
    return dt1_aware == dt2_aware 