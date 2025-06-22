#!/usr/bin/env python3
"""
修复Render上的PostgreSQL数据库时区问题
该脚本将在Render环境中运行，修复数据库中的时区问题
"""
import os
import sys
import psycopg2
import logging
import argparse
from datetime import datetime
import pytz

# 设置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 数据库连接信息
def get_db_params(args=None):
    """获取数据库连接参数，优先从命令行参数读取，其次从环境变量中读取"""
    if args:
        return {
            'dbname': args.dbname or os.environ.get('DATABASE_NAME', ''),
            'user': args.user or os.environ.get('DATABASE_USER', ''),
            'password': args.password or os.environ.get('DATABASE_PASSWORD', ''),
            'host': args.host or os.environ.get('DATABASE_HOST', ''),
            'port': args.port or os.environ.get('DATABASE_PORT', '5432')
        }
    else:
        return {
            'dbname': os.environ.get('DATABASE_NAME', ''),
            'user': os.environ.get('DATABASE_USER', ''),
            'password': os.environ.get('DATABASE_PASSWORD', ''),
            'host': os.environ.get('DATABASE_HOST', ''),
            'port': os.environ.get('DATABASE_PORT', '5432')
        }

def execute_sql_script(conn, cursor, sql):
    """执行SQL脚本"""
    try:
        # 将脚本分割为单独的语句
        statements = sql.split(';')
        
        for statement in statements:
            # 跳过空语句
            if not statement.strip():
                continue
                
            # 打印当前执行的语句（仅显示前100个字符）
            logger.info(f"执行: {statement.strip()[:100]}...")
            
            # 执行语句
            cursor.execute(statement)
        
        # 提交更改
        conn.commit()
        logger.info("SQL脚本执行成功")
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"执行SQL脚本失败: {e}")
        return False

def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='修复Render PostgreSQL数据库时区问题')
    parser.add_argument('--dbname', help='数据库名称')
    parser.add_argument('--user', help='数据库用户名')
    parser.add_argument('--password', help='数据库密码')
    parser.add_argument('--host', help='数据库主机地址')
    parser.add_argument('--port', help='数据库端口号')
    args = parser.parse_args()
    
    logger.info("开始修复Render PostgreSQL数据库时区问题...")
    
    # 获取数据库连接参数
    conn_params = get_db_params(args)
    
    # 检查必要的参数是否存在
    missing_params = [key for key, value in conn_params.items() if not value]
    if missing_params:
        logger.error(f"错误: 以下参数未设置: {', '.join(missing_params)}")
        logger.info("请使用命令行参数提供数据库连接信息，例如:")
        logger.info("python3 fix_render_timezone.py --dbname=mydb --user=myuser --password=mypass --host=myhost --port=5432")
        return 1
    
    # 设置环境变量，标记为Render环境
    os.environ['RENDER'] = 'true'
    
    try:
        # 连接到数据库
        logger.info("正在连接到PostgreSQL数据库...")
        conn = psycopg2.connect(
            dbname=conn_params['dbname'],
            user=conn_params['user'],
            password=conn_params['password'],
            host=conn_params['host'],
            port=conn_params['port']
        )
        cursor = conn.cursor()
        
        # 检查数据库时区设置
        logger.info("检查数据库时区设置...")
        cursor.execute("SHOW timezone;")
        result = cursor.fetchone()
        db_timezone = result[0] if result else "未知"
        logger.info(f"数据库时区: {db_timezone}")
        
        # 检查当前数据库时间
        cursor.execute("SELECT NOW();")
        result = cursor.fetchone()
        db_time = result[0] if result else None
        if db_time:
            logger.info(f"数据库当前时间: {db_time}")
            
            # 获取北京时间
            beijing_now = datetime.now(pytz.timezone('Asia/Shanghai'))
            logger.info(f"北京时间: {beijing_now}")
            
            # 计算时差
            time_diff = (beijing_now - db_time.astimezone(pytz.timezone('Asia/Shanghai'))).total_seconds() / 3600
            logger.info(f"时差(小时): {time_diff:.2f}")
        
        # 设置数据库时区为UTC
        logger.info("设置数据库时区为UTC...")
        cursor.execute("SET timezone TO 'UTC';")
        
        # 验证时区设置
        cursor.execute("SHOW timezone;")
        result = cursor.fetchone()
        new_timezone = result[0] if result else "未知"
        logger.info(f"设置后的数据库时区: {new_timezone}")
        
        # 修复活动表中的时间字段
        logger.info("修复活动表中的时间字段...")
        
        # 1. 修复活动开始时间
        cursor.execute("""
        UPDATE activities
        SET start_time = start_time AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
        WHERE start_time IS NOT NULL;
        """)
        
        # 2. 修复活动结束时间
        cursor.execute("""
        UPDATE activities
        SET end_time = end_time AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
        WHERE end_time IS NOT NULL;
        """)
        
        # 3. 修复活动报名截止时间
        cursor.execute("""
        UPDATE activities
        SET registration_deadline = registration_deadline AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
        WHERE registration_deadline IS NOT NULL;
        """)
        
        # 4. 修复活动创建时间
        cursor.execute("""
        UPDATE activities
        SET created_at = created_at AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
        WHERE created_at IS NOT NULL;
        """)
        
        # 5. 修复活动更新时间
        cursor.execute("""
        UPDATE activities
        SET updated_at = updated_at AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
        WHERE updated_at IS NOT NULL;
        """)
        
        # 修复通知表中的时间字段
        logger.info("修复通知表中的时间字段...")
        
        # 1. 修复通知创建时间
        cursor.execute("""
        UPDATE notification
        SET created_at = created_at AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
        WHERE created_at IS NOT NULL;
        """)
        
        # 2. 修复通知过期时间
        cursor.execute("""
        UPDATE notification
        SET expiry_date = expiry_date AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
        WHERE expiry_date IS NOT NULL;
        """)
        
        # 修复通知已读表中的时间字段
        cursor.execute("""
        UPDATE notification_read
        SET read_at = read_at AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
        WHERE read_at IS NOT NULL;
        """)
        
        # 修复站内信表中的时间字段
        cursor.execute("""
        UPDATE message
        SET created_at = created_at AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
        WHERE created_at IS NOT NULL;
        """)
        
        # 修复报名表中的时间字段
        logger.info("修复报名表中的时间字段...")
        
        # 1. 修复报名时间
        cursor.execute("""
        UPDATE registrations
        SET register_time = register_time AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
        WHERE register_time IS NOT NULL;
        """)
        
        # 2. 修复签到时间
        cursor.execute("""
        UPDATE registrations
        SET check_in_time = check_in_time AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
        WHERE check_in_time IS NOT NULL;
        """)
        
        # 修复系统日志表中的时间字段
        cursor.execute("""
        UPDATE system_logs
        SET created_at = created_at AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
        WHERE created_at IS NOT NULL;
        """)
        
        # 修复积分历史表中的时间字段
        cursor.execute("""
        UPDATE points_history
        SET created_at = created_at AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
        WHERE created_at IS NOT NULL;
        """)
        
        # 修复活动评价表中的时间字段
        cursor.execute("""
        UPDATE activity_reviews
        SET created_at = created_at AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
        WHERE created_at IS NOT NULL;
        """)
        
        # 提交所有更改
        conn.commit()
        logger.info("所有数据库时间字段已修复")
        
        # 验证修复结果
        logger.info("验证修复结果...")
        cursor.execute("""
        SELECT id, title, start_time, end_time, registration_deadline 
        FROM activities 
        ORDER BY created_at DESC 
        LIMIT 3;
        """)
        activities = cursor.fetchall()
        
        for activity in activities:
            if len(activity) >= 5:
                id, title, start_time, end_time, reg_deadline = activity
                logger.info(f"活动 ID: {id}, 标题: {title}")
                logger.info(f"开始时间(UTC): {start_time}")
                
                # 转换为北京时间显示
                if start_time:
                    beijing_start = start_time.astimezone(pytz.timezone('Asia/Shanghai'))
                    logger.info(f"开始时间(北京): {beijing_start.strftime('%Y-%m-%d %H:%M:%S %Z%z')}")
        
        logger.info("时区修复完成!")
        
    except Exception as e:
        logger.error(f"修复过程中出错: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 