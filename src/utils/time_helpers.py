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
    # 使用与get_beijing_time相同的实现方式，确保一致性
    return get_beijing_time()

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
    # 注意：如果代码运行在Render服务器上，默认使用UTC时间，这里需要正确处理
    # 这里我们应该查看数据库中的时间是如何存储的
    # 如果数据库中时间没有时区信息，并且应用程序将其视为UTC，则应该直接添加UTC时区标记
    
    # 检查是否在Render环境下（假设Render环境中已正确设置环境变量）
    if current_app.config.get('IS_RENDER_ENVIRONMENT', False):
        # 在Render环境中，假设输入的dt已经是UTC时间，只需添加时区信息
        return pytz.utc.localize(dt)
    else:
        # 在本地环境中，假设输入的dt是北京时间，需要转换为UTC
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
    beijing_time = dt
    if dt.tzinfo is None:
        # 如果没有时区信息，假设它是UTC时间，转换为北京时间
        beijing_time = pytz.utc.localize(dt).astimezone(pytz.timezone('Asia/Shanghai'))
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
        if current_app.config.get('IS_RENDER_ENVIRONMENT', False):
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