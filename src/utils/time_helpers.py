import logging
import datetime
import pytz
from flask import current_app
from typing import Optional, Union

# 配置日志记录器
logger = logging.getLogger(__name__)

# 北京时区
BEIJING_TIMEZONE = pytz.timezone('Asia/Shanghai')
# UTC时区
UTC_TIMEZONE = pytz.UTC

def get_beijing_time() -> datetime.datetime:
    """
    获取当前北京时间
    
    Returns:
        datetime.datetime: 带有Asia/Shanghai时区信息的当前时间
    """
    utc_now = datetime.datetime.now(UTC_TIMEZONE)
    beijing_time = utc_now.astimezone(BEIJING_TIMEZONE)
    logger.debug(f"当前UTC时间: {utc_now}, 北京时间: {beijing_time}")
    return beijing_time

def is_render_environment():
    """
    检查当前是否在Render环境中运行
    :return: 如果在Render环境中返回True，否则返回False
    """
    import os
    return os.environ.get('RENDER', '') == 'true'

def get_correct_timezone():
    """
    获取正确的时区，Render环境使用UTC，本地环境使用北京时间
    :return: 正确的时区对象
    """
    if is_render_environment():
        return UTC_TIMEZONE
    return BEIJING_TIMEZONE

def localize_time(dt, timezone_name='Asia/Shanghai'):
    """
    将一个datetime对象本地化到指定时区
    :param dt: 需要本地化的datetime对象
    :param timezone_name: 时区名称，默认为北京时间
    :return: 本地化后的datetime对象
    """
    if dt is None:
        return None
        
    # 创建目标时区对象
    target_tz = pytz.timezone(timezone_name)
    
    # 如果dt已经有时区信息，直接转换到目标时区
    if dt.tzinfo is not None:
        return dt.astimezone(target_tz)
    
    # 如果dt没有时区信息，假设它是UTC时间，添加时区信息后转换
    utc_dt = pytz.utc.localize(dt)
    return utc_dt.astimezone(target_tz)

def get_localized_now():
    """
    获取当前UTC时间，带有时区信息
    此函数用于数据库操作，确保存储的时间是带有时区信息的UTC时间
    """
    return datetime.datetime.now(UTC_TIMEZONE)

def ensure_timezone_aware(dt, default_timezone='UTC'):
    """
    确保datetime对象有时区信息，如果没有则添加默认时区
    :param dt: datetime对象
    :param default_timezone: 默认时区名称，建议使用UTC
    :return: 带有时区信息的datetime对象
    """
    if dt is None:
        return None
    
    try:    
        # 检查是否已有时区信息
        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            # 添加默认时区
            tz = pytz.timezone(default_timezone)
            try:
                return tz.localize(dt)
            except (ValueError, AttributeError) as e:
                # 如果localize失败，尝试替代方法
                logger.warning(f"时区本地化失败: {e}, 尝试替代方法")
                aware_dt = dt.replace(tzinfo=tz)
                return aware_dt
        return dt
    except Exception as e:
        logger.error(f"应用时区时发生错误: {e}")
        # 如果无法添加时区，返回原始值
        return dt

def normalize_datetime_for_db(dt: Optional[Union[datetime.datetime, str]]) -> Optional[datetime.datetime]:
    """
    标准化日期时间用于存储到数据库
    
    无论输入是什么时区的datetime对象或字符串，
    统一转换为带有UTC时区信息的时间，以便存储到数据库。
    
    Args:
        dt: 需要标准化的datetime对象或时间字符串
        
    Returns:
        datetime.datetime: 带有UTC时区信息的时间对象
    """
    if dt is None:
        return None
    
    # 如果是字符串，尝试解析为datetime对象
    if isinstance(dt, str):
        try:
            # 尝试多种格式解析
            for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d'):
                try:
                    dt = datetime.datetime.strptime(dt, fmt)
                    # 解析成功后，跳出循环
                    break
                except ValueError:
                    continue
            else:  # 如果所有格式都失败
                logger.error(f"[normalize_datetime_for_db] 无法解析时间字符串: {dt}")
                return None
        except Exception as e:
            logger.error(f"[normalize_datetime_for_db] 时间解析出错: {dt}, 错误: {e}")
            return None
    
    # 处理datetime对象
    if isinstance(dt, datetime.datetime):
        # 如果没有时区信息，假定为北京时间
        if dt.tzinfo is None:
            dt = BEIJING_TIMEZONE.localize(dt)
            logger.info(f"[normalize_datetime_for_db] 添加北京时区信息: {dt}")
        
        # 转换为UTC时间
        utc_dt = dt.astimezone(UTC_TIMEZONE)
        
        # 保留时区信息，返回UTC时间
        logger.info(f"[normalize_datetime_for_db] 原始时间: {dt}, UTC时间: {utc_dt}")
        return utc_dt
    
    logger.error(f"[normalize_datetime_for_db] 不支持的时间类型: {type(dt)}")
    return None

def display_datetime(dt: Optional[Union[datetime.datetime, str]], 
                     timezone: Optional[str] = None, 
                     fmt: str = '%Y-%m-%d %H:%M') -> str:
    """
    格式化datetime对象或字符串，并考虑时区转换
    
    Args:
        dt: 要格式化的datetime对象或字符串
        timezone: 目标时区，默认为Asia/Shanghai（北京时间）
        fmt: 输出格式字符串
        
    Returns:
        str: 格式化后的时间字符串，如果输入无效则返回空字符串
    """
    if dt is None:
        return ""
    
    logger.debug(f"[display_datetime] 输入时间: {dt}, 时区信息: {getattr(dt, 'tzinfo', None)}, 格式: {fmt}")
    
    # 设置目标时区，默认为北京时间
    target_tz = pytz.timezone(timezone) if timezone else BEIJING_TIMEZONE
    
    # 如果是字符串，尝试解析
    if isinstance(dt, str):
        try:
            # 尝试多种格式解析
            for str_fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d'):
                try:
                    dt = datetime.datetime.strptime(dt, str_fmt)
                    break
                except ValueError:
                    continue
            else:
                logger.error(f"[display_datetime] 无法解析时间字符串: {dt}")
                return ""
        except Exception as e:
            logger.error(f"[display_datetime] 解析时间字符串出错: {dt}, 错误: {e}")
            return ""
    
    # 确保dt是datetime类型
    if not isinstance(dt, datetime.datetime):
        logger.error(f"[display_datetime] 不支持的时间类型: {type(dt)}")
        return ""
    
    # 1. 如果是无时区的datetime，必须假定它是UTC时间
    if dt.tzinfo is None:
        try:
            dt = pytz.utc.localize(dt)
            logger.debug(f"[display_datetime] 为无时区时间添加UTC时区: {dt}")
        except Exception as e:
            logger.error(f"[display_datetime] 添加UTC时区失败: {e}")
            # 如果添加时区失败，使用replace方法
            dt = dt.replace(tzinfo=pytz.UTC)
            logger.debug(f"[display_datetime] 使用replace方法添加UTC时区: {dt}")
    
    # 2. 将时间统一转换为北京时间
    dt_in_target_tz = dt.astimezone(target_tz)
    logger.debug(f"[display_datetime] 转换为目标时区后: {dt_in_target_tz}, 时区={target_tz.zone}")
    
    # 3. 按照指定格式输出
    formatted = dt_in_target_tz.strftime(fmt)
    logger.debug(f"[display_datetime] 格式化结果: {formatted}")
    
    return formatted

def format_datetime(dt: Optional[Union[datetime.datetime, str]], fmt: str = '%Y-%m-%d %H:%M') -> str:
    """
    简单格式化datetime对象或字符串，不进行时区转换
    
    Args:
        dt: 要格式化的datetime对象或字符串
        fmt: 输出格式字符串
        
    Returns:
        str: 格式化后的字符串，如果输入无效则返回空字符串
    """
    if dt is None:
        return ""
    
    # 如果是字符串，尝试解析
    if isinstance(dt, str):
        try:
            dt = datetime.datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except ValueError:
            try:
                dt = datetime.datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    dt = datetime.datetime.strptime(dt, '%Y-%m-%d %H:%M')
                except ValueError:
                    try:
                        dt = datetime.datetime.strptime(dt, '%Y-%m-%d')
                    except ValueError:
                        logger.warning(f"无法解析时间字符串: {dt}")
                        return ""
    
    # 确保dt是datetime类型
    if not isinstance(dt, datetime.datetime):
        logger.warning(f"不支持的时间类型: {type(dt)}")
        return ""
    
    # 格式化输出
    return dt.strftime(fmt)

def safe_compare(dt1, dt2):
    """
    安全比较两个datetime对象，确保考虑时区信息
    :param dt1: 第一个datetime对象
    :param dt2: 第二个datetime对象
    :return: 如果相等返回True，否则返回False
    """
    if dt1 is None or dt2 is None:
        return False
    
    # 确保两个时间都有时区信息
    dt1 = ensure_timezone_aware(dt1)
    dt2 = ensure_timezone_aware(dt2)
    
    # 再次检查，确保ensure_timezone_aware没有返回None
    if dt1 is None or dt2 is None:
        return False
    
    # 转换为UTC进行比较
    dt1_utc = dt1.astimezone(UTC_TIMEZONE)
    dt2_utc = dt2.astimezone(UTC_TIMEZONE)
    
    return dt1_utc == dt2_utc

def safe_less_than(dt1, dt2):
    """
    安全比较两个datetime对象，确保考虑时区信息
    :param dt1: 第一个datetime对象
    :param dt2: 第二个datetime对象
    :return: 如果dt1 < dt2返回True，否则返回False
    """
    if dt1 is None or dt2 is None:
        return False
    
    # 确保两个时间都有时区信息
    dt1 = ensure_timezone_aware(dt1)
    dt2 = ensure_timezone_aware(dt2)
    
    # 再次检查，确保ensure_timezone_aware没有返回None
    if dt1 is None or dt2 is None:
        return False
    
    # 转换为UTC进行比较
    dt1_utc = dt1.astimezone(UTC_TIMEZONE)
    dt2_utc = dt2.astimezone(UTC_TIMEZONE)
    
    return dt1_utc < dt2_utc

def safe_greater_than(dt1, dt2):
    """
    安全比较两个datetime对象，确保考虑时区信息
    :param dt1: 第一个datetime对象
    :param dt2: 第二个datetime对象
    :return: 如果dt1 > dt2返回True，否则返回False
    """
    if dt1 is None or dt2 is None:
        return False
    
    # 确保两个时间都有时区信息
    dt1 = ensure_timezone_aware(dt1)
    dt2 = ensure_timezone_aware(dt2)
    
    # 再次检查，确保ensure_timezone_aware没有返回None
    if dt1 is None or dt2 is None:
        return False
    
    # 转换为UTC进行比较
    dt1_utc = dt1.astimezone(UTC_TIMEZONE)
    dt2_utc = dt2.astimezone(UTC_TIMEZONE)
    
    return dt1_utc > dt2_utc

def time_is_past(dt: Optional[Union[datetime.datetime, str]]) -> bool:
    """
    检查给定的时间是否已经过去
    
    Args:
        dt: 要检查的时间，可以是datetime对象或字符串
        
    Returns:
        bool: 如果时间已经过去则返回True，否则返回False
    """
    if dt is None:
        return False
    
    # 获取当前UTC时间
    now = get_localized_now()
    
    # 如果是字符串，尝试解析
    if isinstance(dt, str):
        try:
            dt = datetime.datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except ValueError:
            try:
                dt = datetime.datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    dt = datetime.datetime.strptime(dt, '%Y-%m-%d %H:%M')
                except ValueError:
                    try:
                        dt = datetime.datetime.strptime(dt, '%Y-%m-%d')
                    except ValueError:
                        logger.warning(f"无法解析时间字符串: {dt}")
                        return False
    
    # 确保dt是datetime类型
    if not isinstance(dt, datetime.datetime):
        logger.warning(f"不支持的时间类型: {type(dt)}")
        return False
    
    # 确保时间有时区信息
    dt = ensure_timezone_aware(dt)
    
    # 检查ensure_timezone_aware是否返回了None
    if dt is None:
        return False
    
    # 比较时间
    return dt < now

def time_is_future(dt: Optional[Union[datetime.datetime, str]]) -> bool:
    """
    检查给定的时间是否在未来
    
    Args:
        dt: 要检查的时间，可以是datetime对象或字符串
        
    Returns:
        bool: 如果时间在未来则返回True，否则返回False
    """
    return not time_is_past(dt)

def safe_time_compare(time1: Optional[Union[datetime.datetime, str]], 
                     time2: Optional[Union[datetime.datetime, str]]) -> int:
    """
    安全比较两个时间，返回比较结果
    
    Args:
        time1: 第一个时间，可以是datetime对象或字符串
        time2: 第二个时间，可以是datetime对象或字符串
        
    Returns:
        int: 如果time1 < time2返回-1，如果time1 == time2返回0，如果time1 > time2返回1
    """
    # 处理None值
    if time1 is None and time2 is None:
        return 0
    if time1 is None:
        return -1
    if time2 is None:
        return 1
    
    # 处理字符串
    if isinstance(time1, str):
        try:
            time1 = datetime.datetime.fromisoformat(time1.replace('Z', '+00:00'))
        except ValueError:
            try:
                time1 = datetime.datetime.strptime(time1, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    time1 = datetime.datetime.strptime(time1, '%Y-%m-%d %H:%M')
                except ValueError:
                    try:
                        time1 = datetime.datetime.strptime(time1, '%Y-%m-%d')
                    except ValueError:
                        logger.warning(f"无法解析时间字符串: {time1}")
                        return 0  # 无法解析时返回相等
    
    if isinstance(time2, str):
        try:
            time2 = datetime.datetime.fromisoformat(time2.replace('Z', '+00:00'))
        except ValueError:
            try:
                time2 = datetime.datetime.strptime(time2, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    time2 = datetime.datetime.strptime(time2, '%Y-%m-%d %H:%M')
                except ValueError:
                    try:
                        time2 = datetime.datetime.strptime(time2, '%Y-%m-%d')
                    except ValueError:
                        logger.warning(f"无法解析时间字符串: {time2}")
                        return 0  # 无法解析时返回相等
    
    # 确保两个时间都有时区信息
    time1 = ensure_timezone_aware(time1)
    time2 = ensure_timezone_aware(time2)
    
    # 检查ensure_timezone_aware是否返回了None
    if time1 is None or time2 is None:
        return 0  # 如果转换失败，返回相等
    
    # 转换为UTC进行比较
    time1_utc = time1.astimezone(UTC_TIMEZONE)
    time2_utc = time2.astimezone(UTC_TIMEZONE)
    
    if time1_utc < time2_utc:
        return -1
    elif time1_utc > time2_utc:
        return 1
    else:
        return 0