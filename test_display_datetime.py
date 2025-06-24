#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试display_datetime函数
"""

import os
import sys
import datetime
import pytz
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# 导入display_datetime函数
from src.utils.time_helpers import display_datetime

# 创建测试用例
def test_display_datetime():
    # 创建一个UTC时间
    dt = datetime.datetime(2025, 6, 24, 10, 0, 0, tzinfo=pytz.UTC)
    
    # 测试只有一个参数
    result1 = display_datetime(dt)
    print(f"Test 1 - 只有dt参数: {result1}")
    
    # 测试两个参数 - 第二个参数是格式
    result2 = display_datetime(dt, '%Y-%m-%d')
    print(f"Test 2 - dt和格式参数: {result2}")
    
    # 测试两个参数 - 第二个参数是时区
    result3 = display_datetime(dt, 'America/New_York')
    print(f"Test 3 - dt和时区参数: {result3}")
    
    # 测试三个参数
    result4 = display_datetime(dt, 'America/New_York', '%Y-%m-%d %H:%M:%S')
    print(f"Test 4 - dt、时区和格式参数: {result4}")
    
    # 测试模板中的实际调用方式
    result5 = display_datetime(dt, 'Asia/Shanghai', '%Y-%m-%d')
    print(f"Test 5 - 模板中的调用方式: {result5}")

if __name__ == "__main__":
    print("开始测试display_datetime函数...")
    test_display_datetime()
    print("测试完成") 