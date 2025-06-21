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
    # 检查是否在Render环境，如果是，返回UTC时间，否则返回北京时间
    if is_render_environment():
        return datetime.datetime.utcnow()
    else:
        return get_beijing_time().replace(tzinfo=None)

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
        # 检查是否在Render环境下
        if is_render_environment():
            # 在Render环境中，假设naive时间已经是UTC
            return pytz.utc.localize(dt)
        else:
            # 在本地环境，按照默认时区处理
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
        # 确保dt1和dt2不为None后再调用timestamp()
        if dt1 and dt2:
            ts1 = dt1.timestamp()
            ts2 = dt2.timestamp()
            
            if ts1 < ts2:
                return -1
            elif ts1 > ts2:
                return 1
            else:
                return 0
        else:
            # 如果dt1或dt2为None，使用字符串比较
            str1 = str(dt1)
            str2 = str(dt2)
            if str1 < str2:
                return -1
            elif str1 > str2:
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

def is_render_environment():
    """
    检查是否在Render环境中运行
    :return: 布尔值
    """
    try:
        return current_app.config.get('IS_RENDER_ENVIRONMENT', False)
    except RuntimeError:
        # 如果在应用上下文外部调用，则检查环境变量
        import os
        return os.environ.get('RENDER', False) or os.environ.get('IS_RENDER', False)

def normalize_datetime_for_db(dt):
    """
    规范化datetime对象，以便存储到数据库中
    对于Render环境，返回UTC时间（无时区信息）
    对于本地环境，返回本地时间（无时区信息）
    :param dt: datetime对象
    :return: 规范化后的datetime对象
    """
    if dt is None:
        return None
        
    # 将时间转换为UTC，并去除时区信息
    return convert_to_utc(dt) 