import datetime
import pytz
from flask import current_app
import logging

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
    :param dt: datetime对象
    :return: 规范化后的datetime对象
    """
    if dt is None:
        return None
    
    # 确保时间有时区信息
    aware_dt = ensure_timezone_aware(dt)
    
    # 确保aware_dt不是None
    if aware_dt is None:
        return None
    
    # 在Render环境中，我们直接保留北京时间
    if is_render_environment():
        # 确保是北京时间
        beijing_tz = pytz.timezone('Asia/Shanghai')
        if aware_dt.tzinfo is not None:
            beijing_dt = aware_dt.astimezone(beijing_tz)
        else:
            beijing_dt = beijing_tz.localize(aware_dt)
        
        # 保留时区信息，不要去除
        return beijing_dt
    else:
        # 本地环境，转换为UTC并去除时区信息
        utc_dt = aware_dt.astimezone(pytz.utc).replace(tzinfo=None)
        return utc_dt

def display_datetime(dt, timezone_or_fmt=None, fmt=None):
    """
    将UTC时间转换为指定时区并格式化
    
    Args:
        dt: 日期时间对象，可能是naive或aware
        timezone_or_fmt: 时区名称或格式化字符串，如果是格式化字符串，则忽略fmt参数
        fmt: 格式化字符串，如果不提供则使用默认格式
        
    Returns:
        str: 格式化后的时间字符串
    """
    if dt is None:
        return "未设置"
    
    # 判断第二个参数是时区名称还是格式化字符串
    actual_fmt = '%Y-%m-%d %H:%M'  # 默认格式
    timezone = 'Asia/Shanghai'  # 默认时区
    
    if timezone_or_fmt:
        if '/' in timezone_or_fmt or timezone_or_fmt in pytz.all_timezones:
            # 这是时区名称
            timezone = timezone_or_fmt
            if fmt:
                actual_fmt = fmt
        else:
            # 这是格式化字符串
            actual_fmt = timezone_or_fmt
    
    # 获取时区对象
    try:
        tz = pytz.timezone(timezone)
    except:
        tz = pytz.timezone('Asia/Shanghai')  # 如果时区名称无效，使用默认时区
    
    # 确保dt有时区信息
    if dt.tzinfo is None:
        # 无时区信息，假定为UTC
        try:
            dt = pytz.utc.localize(dt)
        except (ValueError, AttributeError):
            # 如果已经有时区但不是UTC，则转换为UTC
            dt = dt.replace(tzinfo=pytz.UTC)
    
    # 转换为指定时区
    local_time = dt.astimezone(tz)
    
    # 格式化
    return local_time.strftime(actual_fmt)

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

def safe_greater_than(dt1, dt2):
    """
    安全比较dt1是否大于dt2，处理时区问题
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
    
    return dt1_aware > dt2_aware

def safe_less_than(dt1, dt2):
    """
    安全比较dt1是否小于dt2，处理时区问题
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
    
    return dt1_aware < dt2_aware

def safe_greater_than_equal(dt1, dt2):
    """
    安全比较dt1是否大于等于dt2，处理时区问题
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
    
    return dt1_aware >= dt2_aware

def safe_less_than_equal(dt1, dt2):
    """
    安全比较dt1是否小于等于dt2，处理时区问题
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
    
    return dt1_aware <= dt2_aware 