#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本
从源数据库完全迁移到目标数据库
"""

import os
import sys
import subprocess
import psycopg2
from psycopg2 import sql
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 数据库连接配置
SOURCE_DB = {
    'host': 'dbprovider.ap-northeast-1.clawcloudrun.com',
    'port': '38988',
    'database': 'postgres',
    'user': 'postgres',
    'password': 'slxjfzvk'
}

TARGET_DB = {
    'host': 'dpg-d2m92d0gjchc73f7322g-a.oregon-postgres.render.com',
    'port': '5432',
    'database': 'cqnureg4',
    'user': 'cqnureg4_user',
    'password': 'ngaPERNcFzyxhuiMKCofSlsnM7w6AeNG'
}

def test_connection(db_config, db_name):
    """测试数据库连接"""
    try:
        conn = psycopg2.connect(**db_config)
        conn.close()
        logger.info(f"✅ {db_name}数据库连接成功")
        return True
    except Exception as e:
        logger.error(f"❌ {db_name}数据库连接失败: {e}")
        return False

def get_table_list(db_config):
    """获取数据库中的所有表"""
    try:
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        
        # 获取所有用户表（排除系统表）
        cur.execute("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename;
        """)
        
        tables = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        
        logger.info(f"找到 {len(tables)} 个表: {', '.join(tables)}")
        return tables
    except Exception as e:
        logger.error(f"获取表列表失败: {e}")
        return []

def export_database():
    """导出源数据库"""
    logger.info("开始导出源数据库...")
    
    # 构建pg_dump命令
    dump_file = f"database_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
    
    cmd = [
        'pg_dump',
        f"--host={SOURCE_DB['host']}",
        f"--port={SOURCE_DB['port']}",
        f"--username={SOURCE_DB['user']}",
        f"--dbname={SOURCE_DB['database']}",
        '--verbose',
        '--clean',
        '--no-owner',
        '--no-privileges',
        '--format=plain',
        f"--file={dump_file}"
    ]
    
    # 设置密码环境变量
    env = os.environ.copy()
    env['PGPASSWORD'] = SOURCE_DB['password']
    
    try:
        logger.info(f"执行命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"✅ 数据库导出成功: {dump_file}")
            return dump_file
        else:
            logger.error(f"❌ 数据库导出失败: {result.stderr}")
            return None
    except Exception as e:
        logger.error(f"导出过程中发生错误: {e}")
        return None

def import_database(dump_file):
    """导入数据到目标数据库"""
    logger.info(f"开始导入数据到目标数据库: {dump_file}")
    
    # 构建psql命令
    cmd = [
        'psql',
        f"--host={TARGET_DB['host']}",
        f"--port={TARGET_DB['port']}",
        f"--username={TARGET_DB['user']}",
        f"--dbname={TARGET_DB['database']}",
        f"--file={dump_file}"
    ]
    
    # 设置密码环境变量
    env = os.environ.copy()
    env['PGPASSWORD'] = TARGET_DB['password']
    
    try:
        logger.info(f"执行命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("✅ 数据库导入成功")
            return True
        else:
            logger.error(f"❌ 数据库导入失败: {result.stderr}")
            logger.info(f"导入输出: {result.stdout}")
            return False
    except Exception as e:
        logger.error(f"导入过程中发生错误: {e}")
        return False

def verify_migration():
    """验证迁移结果"""
    logger.info("验证迁移结果...")
    
    try:
        # 获取源数据库表列表
        source_tables = get_table_list(SOURCE_DB)
        
        # 获取目标数据库表列表
        target_tables = get_table_list(TARGET_DB)
        
        # 比较表数量
        logger.info(f"源数据库表数量: {len(source_tables)}")
        logger.info(f"目标数据库表数量: {len(target_tables)}")
        
        # 检查缺失的表
        missing_tables = set(source_tables) - set(target_tables)
        if missing_tables:
            logger.warning(f"目标数据库缺失的表: {', '.join(missing_tables)}")
        
        # 检查每个表的记录数
        for table in source_tables:
            if table in target_tables:
                source_count = get_table_count(SOURCE_DB, table)
                target_count = get_table_count(TARGET_DB, table)
                
                if source_count == target_count:
                    logger.info(f"✅ 表 {table}: {source_count} 条记录 (匹配)")
                else:
                    logger.warning(f"⚠️ 表 {table}: 源 {source_count} vs 目标 {target_count} 条记录")
        
        return len(missing_tables) == 0
        
    except Exception as e:
        logger.error(f"验证过程中发生错误: {e}")
        return False

def get_table_count(db_config, table_name):
    """获取表的记录数"""
    try:
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        
        cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(
            sql.Identifier(table_name)
        ))
        
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        
        return count
    except Exception as e:
        logger.error(f"获取表 {table_name} 记录数失败: {e}")
        return -1

def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("开始数据库迁移")
    logger.info("=" * 50)
    
    # 1. 测试连接
    logger.info("步骤 1: 测试数据库连接")
    if not test_connection(SOURCE_DB, "源"):
        logger.error("源数据库连接失败，终止迁移")
        return False
    
    if not test_connection(TARGET_DB, "目标"):
        logger.error("目标数据库连接失败，终止迁移")
        return False
    
    # 2. 导出数据库
    logger.info("步骤 2: 导出源数据库")
    dump_file = export_database()
    if not dump_file:
        logger.error("数据库导出失败，终止迁移")
        return False
    
    # 3. 导入数据库
    logger.info("步骤 3: 导入到目标数据库")
    if not import_database(dump_file):
        logger.error("数据库导入失败")
        return False
    
    # 4. 验证迁移
    logger.info("步骤 4: 验证迁移结果")
    if verify_migration():
        logger.info("✅ 数据库迁移完成并验证成功")
    else:
        logger.warning("⚠️ 数据库迁移完成但验证发现问题")
    
    # 5. 清理临时文件
    try:
        os.remove(dump_file)
        logger.info(f"清理临时文件: {dump_file}")
    except:
        pass
    
    logger.info("=" * 50)
    logger.info("数据库迁移流程结束")
    logger.info("=" * 50)
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)