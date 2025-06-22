#!/usr/bin/env python3
import os
import sys
import pytz
from datetime import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

# 创建一个简单的Flask应用
app = Flask(__name__)

# 配置数据库连接
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'postgresql://cqnu_association_uxft_user:BamPWSRTgj0sPGKM4sGsLDv8sGCPCPzB@dpg-d0sjag49c44c73f7jt4g-a.oregon-postgres.render.com/cqnu_association_uxft'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化SQLAlchemy
db = SQLAlchemy(app)

def test_database_connection():
    """测试数据库连接"""
    print("测试数据库连接...")
    try:
        # 执行简单查询
        result = db.session.execute(text("SELECT 1")).fetchone()
        if result and result[0] == 1:
            print("✅ 数据库连接成功")
            return True
        else:
            print("❌ 数据库连接失败")
            return False
    except Exception as e:
        print(f"❌ 数据库连接错误: {e}")
        return False

def test_database_timezone():
    """测试数据库时区设置"""
    print("\n测试数据库时区设置...")
    try:
        # 获取数据库时区
        result = db.session.execute(text("SHOW timezone")).fetchone()
        db_timezone = result[0] if result else "未知"
        print(f"数据库时区: {db_timezone}")
        
        # 获取数据库当前时间
        result = db.session.execute(text("SELECT NOW()")).fetchone()
        db_time = result[0] if result else None
        
        if db_time:
            print(f"数据库当前时间: {db_time}")
            
            # 获取本地北京时间
            beijing_now = datetime.now(pytz.timezone('Asia/Shanghai'))
            print(f"本地北京时间: {beijing_now}")
            
            # 计算时差
            time_diff = abs((beijing_now - db_time.astimezone(pytz.timezone('Asia/Shanghai'))).total_seconds() / 60)
            print(f"时差(分钟): {time_diff:.2f}")
            
            if time_diff < 5:  # 允许5分钟的误差
                print("✅ 数据库时间与北京时间基本一致")
            else:
                print("❌ 数据库时间与北京时间相差较大")
        
        return True
    except Exception as e:
        print(f"❌ 测试数据库时区错误: {e}")
        return False

def test_activity_times():
    """测试活动时间是否正确"""
    print("\n测试活动时间...")
    try:
        # 获取最新的活动
        result = db.session.execute(text("""
            SELECT id, title, start_time, end_time, registration_deadline 
            FROM activities 
            ORDER BY created_at DESC 
            LIMIT 3
        """)).fetchall()
        
        if not result:
            print("没有找到活动数据")
            return True
        
        for row in result:
            id, title, start_time, end_time, reg_deadline = row
            print(f"\n活动ID: {id}, 标题: {title}")
            
            # 检查时间格式
            if start_time:
                print(f"开始时间(原始): {start_time}")
                # 转换为北京时间
                beijing_start = start_time.astimezone(pytz.timezone('Asia/Shanghai'))
                print(f"开始时间(北京): {beijing_start.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            
            if end_time:
                print(f"结束时间(原始): {end_time}")
                # 转换为北京时间
                beijing_end = end_time.astimezone(pytz.timezone('Asia/Shanghai'))
                print(f"结束时间(北京): {beijing_end.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            
            if reg_deadline:
                print(f"报名截止(原始): {reg_deadline}")
                # 转换为北京时间
                beijing_deadline = reg_deadline.astimezone(pytz.timezone('Asia/Shanghai'))
                print(f"报名截止(北京): {beijing_deadline.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        print("\n✅ 活动时间测试完成")
        return True
    except Exception as e:
        print(f"❌ 测试活动时间错误: {e}")
        return False

def test_timezone_conversion():
    """测试时区转换函数"""
    print("\n测试时区转换函数...")
    try:
        # 创建一个UTC时间
        utc_now = datetime.now(pytz.UTC)
        print(f"UTC时间: {utc_now}")
        
        # 转换为北京时间
        beijing_now = utc_now.astimezone(pytz.timezone('Asia/Shanghai'))
        print(f"北京时间: {beijing_now}")
        
        # 检查时差是否为8小时
        time_diff = (beijing_now.hour - utc_now.hour) % 24
        if time_diff == 8:
            print("✅ 时区转换正确，北京时间比UTC快8小时")
        else:
            print(f"❌ 时区转换异常，时差为{time_diff}小时")
        
        return True
    except Exception as e:
        print(f"❌ 测试时区转换错误: {e}")
        return False

def main():
    """主函数"""
    print("开始时区修复验证测试...\n")
    
    # 设置环境变量，标记为Render环境
    os.environ['RENDER'] = 'true'
    
    # 测试数据库连接
    if not test_database_connection():
        return 1
    
    # 测试数据库时区
    test_database_timezone()
    
    # 测试活动时间
    test_activity_times()
    
    # 测试时区转换
    test_timezone_conversion()
    
    print("\n时区修复验证测试完成")
    return 0

if __name__ == "__main__":
    with app.app_context():
        sys.exit(main()) 