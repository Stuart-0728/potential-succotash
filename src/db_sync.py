"""
数据库同步脚本
用于在主数据库和备份数据库之间同步数据
"""
import os
import sys
import logging
import json
import subprocess
from datetime import datetime
from sqlalchemy import create_engine, text, MetaData, Table
from sqlalchemy.orm import sessionmaker
import psycopg2
from psycopg2.extras import RealDictCursor

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.dual_db_config import dual_db

logger = logging.getLogger(__name__)

class DatabaseSyncer:
    """数据库同步器"""
    
    def __init__(self):
        self.dual_db = dual_db
        self.sync_log = []
    
    def log_sync_action(self, action, status, details=None):
        """记录同步操作"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'status': status,
            'details': details
        }
        self.sync_log.append(log_entry)
        logger.info(f"同步操作: {action} - {status}")
        if details:
            logger.info(f"详情: {details}")
    
    def backup_to_clawcloud(self):
        """将主数据库备份到ClawCloud - 简化版本"""
        if not self.dual_db.is_dual_db_enabled():
            self.log_sync_action("备份到ClawCloud", "失败", "双数据库未配置")
            return False

        try:
            self.log_sync_action("开始备份", "进行中", "连接数据库")

            # 测试数据库连接
            try:
                from sqlalchemy import create_engine, text
                primary_engine = create_engine(self.dual_db.primary_db_url, connect_args={'connect_timeout': 10})
                backup_engine = create_engine(self.dual_db.backup_db_url, connect_args={'connect_timeout': 10})

                # 测试连接
                with primary_engine.connect() as conn:
                    conn.execute(text('SELECT 1'))
                with backup_engine.connect() as conn:
                    conn.execute(text('SELECT 1'))

                self.log_sync_action("数据库连接", "成功", "主数据库和备份数据库连接正常")

            except Exception as e:
                self.log_sync_action("数据库连接", "失败", f"连接错误: {str(e)}")
                return False

            # 获取要同步的表
            tables_to_sync = [
                'users', 'roles', 'activities', 'activity_registrations',
                'notifications', 'system_logs', 'messages', 'tags',
                'user_tags', 'activity_tags', 'checkin_records'
            ]

            synced_tables = 0
            total_rows = 0

            with primary_engine.connect() as primary_conn, backup_engine.connect() as backup_conn:
                for table_name in tables_to_sync:
                    try:
                        self.log_sync_action(f"同步表 {table_name}", "开始")

                        # 检查表是否存在
                        check_sql = text(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table_name}')")
                        primary_exists = primary_conn.execute(check_sql).scalar()
                        backup_exists = backup_conn.execute(check_sql).scalar()

                        if not primary_exists:
                            self.log_sync_action(f"跳过表 {table_name}", "跳过", "主数据库中不存在")
                            continue

                        if not backup_exists:
                            self.log_sync_action(f"跳过表 {table_name}", "跳过", "备份数据库中不存在")
                            continue

                        # 清空备份表
                        backup_conn.execute(text(f'DELETE FROM "{table_name}"'))
                        backup_conn.commit()

                        # 获取主表数据
                        result = primary_conn.execute(text(f'SELECT * FROM "{table_name}"'))
                        rows = result.fetchall()

                        if rows:
                            # 获取列名
                            columns = result.keys()
                            column_names = ', '.join([f'"{col}"' for col in columns])

                            # 简单插入数据（避免复杂的批量操作）
                            for row in rows:
                                placeholders = ', '.join(['%s'] * len(columns))
                                insert_sql = f'INSERT INTO "{table_name}" ({column_names}) VALUES ({placeholders})'
                                backup_conn.execute(text(insert_sql), tuple(row))

                        backup_conn.commit()
                        synced_tables += 1
                        total_rows += len(rows)
                        self.log_sync_action(f"同步表 {table_name}", "成功", f"{len(rows)} 行数据")

                    except Exception as e:
                        self.log_sync_action(f"同步表 {table_name}", "失败", str(e))
                        # 继续处理下一个表，不中断整个过程
                        continue

            self.log_sync_action("备份到ClawCloud", "成功",
                               f"同步了 {synced_tables} 个表，共 {total_rows} 行数据")
            return True

        except Exception as e:
            self.log_sync_action("备份到ClawCloud", "失败", str(e))
            logger.error(f"备份失败: {e}")
            return False
    
    def restore_from_clawcloud(self):
        """从ClawCloud恢复到主数据库 - 简化版本"""
        if not self.dual_db.is_dual_db_enabled():
            self.log_sync_action("从ClawCloud恢复", "失败", "双数据库未配置")
            return False

        try:
            self.log_sync_action("开始恢复", "进行中", "连接数据库")

            # 测试数据库连接
            try:
                from sqlalchemy import create_engine, text
                primary_engine = create_engine(self.dual_db.primary_db_url, connect_args={'connect_timeout': 10})
                backup_engine = create_engine(self.dual_db.backup_db_url, connect_args={'connect_timeout': 10})

                # 测试连接
                with primary_engine.connect() as conn:
                    conn.execute(text('SELECT 1'))
                with backup_engine.connect() as conn:
                    conn.execute(text('SELECT 1'))

                self.log_sync_action("数据库连接", "成功", "主数据库和备份数据库连接正常")

            except Exception as e:
                self.log_sync_action("数据库连接", "失败", f"连接错误: {str(e)}")
                return False

            # 获取要恢复的表
            tables_to_restore = [
                'users', 'roles', 'activities', 'activity_registrations',
                'notifications', 'system_logs', 'messages', 'tags',
                'user_tags', 'activity_tags', 'checkin_records'
            ]

            restored_tables = 0
            total_rows = 0

            with backup_engine.connect() as backup_conn, primary_engine.connect() as primary_conn:
                for table_name in tables_to_restore:
                    try:
                        self.log_sync_action(f"恢复表 {table_name}", "开始")

                        # 检查表是否存在
                        check_sql = text(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table_name}')")
                        backup_exists = backup_conn.execute(check_sql).scalar()
                        primary_exists = primary_conn.execute(check_sql).scalar()

                        if not backup_exists:
                            self.log_sync_action(f"跳过表 {table_name}", "跳过", "备份数据库中不存在")
                            continue

                        if not primary_exists:
                            self.log_sync_action(f"跳过表 {table_name}", "跳过", "主数据库中不存在")
                            continue

                        # 清空主表
                        primary_conn.execute(text(f'DELETE FROM "{table_name}"'))
                        primary_conn.commit()

                        # 获取备份表数据
                        result = backup_conn.execute(text(f'SELECT * FROM "{table_name}"'))
                        rows = result.fetchall()

                        if rows:
                            # 获取列名
                            columns = result.keys()
                            column_names = ', '.join([f'"{col}"' for col in columns])

                            # 简单插入数据（避免复杂的批量操作）
                            for row in rows:
                                placeholders = ', '.join(['%s'] * len(columns))
                                insert_sql = f'INSERT INTO "{table_name}" ({column_names}) VALUES ({placeholders})'
                                primary_conn.execute(text(insert_sql), tuple(row))

                        primary_conn.commit()
                        restored_tables += 1
                        total_rows += len(rows)
                        self.log_sync_action(f"恢复表 {table_name}", "成功", f"{len(rows)} 行数据")

                    except Exception as e:
                        self.log_sync_action(f"恢复表 {table_name}", "失败", str(e))
                        # 继续处理下一个表，不中断整个过程
                        continue

            self.log_sync_action("从ClawCloud恢复", "成功",
                               f"恢复了 {restored_tables} 个表，共 {total_rows} 行数据")
            return True

        except Exception as e:
            self.log_sync_action("从ClawCloud恢复", "失败", str(e))
            logger.error(f"恢复失败: {e}")
            return False
    
    def get_sync_log(self):
        """获取同步日志"""
        return self.sync_log
    
    def save_sync_log(self, filename=None):
        """保存同步日志到文件"""
        if not filename:
            filename = f"sync_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.sync_log, f, ensure_ascii=False, indent=2)
            return filename
        except Exception as e:
            logger.error(f"保存同步日志失败: {e}")
            return None

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='数据库同步工具')
    parser.add_argument('action', choices=['backup', 'restore', 'test'], 
                       help='操作类型: backup(备份到ClawCloud), restore(从ClawCloud恢复), test(测试连接)')
    
    args = parser.parse_args()
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    syncer = DatabaseSyncer()
    
    if args.action == 'test':
        print("测试数据库连接...")
        info = dual_db.get_database_info()
        print(json.dumps(info, indent=2, ensure_ascii=False))
    
    elif args.action == 'backup':
        print("开始备份到ClawCloud...")
        success = syncer.backup_to_clawcloud()
        if success:
            print("备份成功完成!")
        else:
            print("备份失败!")
            sys.exit(1)
    
    elif args.action == 'restore':
        print("开始从ClawCloud恢复...")
        success = syncer.restore_from_clawcloud()
        if success:
            print("恢复成功完成!")
        else:
            print("恢复失败!")
            sys.exit(1)
    
    # 保存同步日志
    log_file = syncer.save_sync_log()
    if log_file:
        print(f"同步日志已保存到: {log_file}")

if __name__ == '__main__':
    main()
