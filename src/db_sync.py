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
from src.utils.time_helpers import get_beijing_time

logger = logging.getLogger(__name__)

class DatabaseSyncer:
    """数据库同步器"""
    
    def __init__(self):
        self.dual_db = dual_db
        self.sync_log = []
    
    def log_sync_action(self, action, status, details=None):
        """记录同步操作"""
        # 使用北京时间
        beijing_time = get_beijing_time()
        # 强制确保时区信息包含在时间戳中
        if beijing_time.tzinfo is None:
            # 如果没有时区信息，手动添加
            import pytz
            beijing_tz = pytz.timezone('Asia/Shanghai')
            beijing_time = beijing_tz.localize(beijing_time)

        # 使用ISO 8601格式，确保包含时区信息
        timestamp_str = beijing_time.isoformat()
        log_entry = {
            'timestamp': timestamp_str,
            'action': action,
            'status': status,
            'details': details
        }
        self.sync_log.append(log_entry)
        # 记录操作日志
        logger.info(f"同步操作: {action} - {status}")
        if details:
            logger.info(f"详情: {details}")
    
    def backup_to_clawcloud(self):
        """将主数据库备份到ClawCloud - 优化版本"""
        import time
        start_time = time.time()
        max_duration = 150  # 最大150秒执行时间（2.5分钟，确保在前端3分钟超时前完成）

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

            # 获取要同步的表（按优先级和大小排序）
            # 优先同步小表，最后同步大表
            tables_to_sync = [
                # 第一阶段：基础小表（快速同步）
                'roles', 'tags',
                # 第二阶段：用户和活动表（中等大小）
                'users', 'activities',
                # 第三阶段：关联表（通常较小）
                'activity_tags', 'user_tags',
                # 第四阶段：会话表（中等大小）
                'ai_chat_session', 'ai_chat_message',
                # 第五阶段：其他依赖表（较小）
                'activity_registrations', 'checkin_records', 'messages', 'notifications',
                # 最后阶段：大表（可能很慢）
                'system_logs'  # 通常是最大的表，放在最后
            ]

            synced_tables = 0
            total_rows = 0

            with primary_engine.connect() as primary_conn, backup_engine.connect() as backup_conn:
                # 禁用外键约束检查（PostgreSQL）
                try:
                    backup_conn.execute(text('SET session_replication_role = replica'))
                    backup_conn.commit()
                    self.log_sync_action("禁用外键约束", "成功", "临时禁用外键约束检查")
                except Exception as e:
                    self.log_sync_action("禁用外键约束", "警告", f"无法禁用外键约束: {str(e)}")

                try:
                    total_tables = len(tables_to_sync)
                    for index, table_name in enumerate(tables_to_sync, 1):
                        # 检查超时
                        if time.time() - start_time > max_duration:
                            self.log_sync_action("同步超时", "警告", f"已运行{max_duration}秒，停止同步")
                            break
                        try:
                            self.log_sync_action(f"同步表 {table_name} ({index}/{total_tables})", "开始")

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

                            # 清空备份表（使用TRUNCATE CASCADE处理外键约束）
                            try:
                                backup_conn.execute(text(f'TRUNCATE TABLE "{table_name}" CASCADE'))
                            except Exception as truncate_error:
                                # 如果TRUNCATE失败，尝试DELETE
                                self.log_sync_action(f"TRUNCATE {table_name} 失败，尝试DELETE", "警告", str(truncate_error))
                                backup_conn.execute(text(f'DELETE FROM "{table_name}"'))

                            # 获取主表数据
                            result = primary_conn.execute(text(f'SELECT * FROM "{table_name}"'))
                            rows = result.fetchall()

                            if rows:
                                # 获取列名
                                columns = result.keys()
                                column_names = ', '.join([f'"{col}"' for col in columns])

                                # 使用更高效的批量插入 - 简化版本
                                # 直接使用批量插入，避免COPY的复杂性
                                self._batch_insert_fallback(backup_conn, table_name, columns, column_names, rows)

                            synced_tables += 1
                            total_rows += len(rows)
                            self.log_sync_action(f"同步表 {table_name}", "成功", f"{len(rows)} 行数据")

                        except Exception as e:
                            self.log_sync_action(f"同步表 {table_name}", "失败", str(e))
                            # 记录错误但继续处理其他表
                            continue

                    # 重新启用外键约束检查
                    try:
                        backup_conn.execute(text('SET session_replication_role = DEFAULT'))
                        backup_conn.commit()
                        self.log_sync_action("恢复外键约束", "成功", "重新启用外键约束检查")
                    except Exception as e:
                        self.log_sync_action("恢复外键约束", "警告", f"无法恢复外键约束: {str(e)}")

                except Exception as e:
                    # 确保恢复外键约束
                    try:
                        backup_conn.execute(text('SET session_replication_role = DEFAULT'))
                        backup_conn.commit()
                    except:
                        pass

                    self.log_sync_action("数据库同步", "失败", f"同步过程失败: {str(e)}")
                    synced_tables = 0  # 确保返回失败状态

            if synced_tables > 0:
                self.log_sync_action("备份到ClawCloud", "成功",
                                   f"同步了 {synced_tables} 个表，共 {total_rows} 行数据")
                return True
            else:
                self.log_sync_action("备份到ClawCloud", "失败",
                                   "没有成功同步任何表，请检查数据库连接和权限")
                return False

        except Exception as e:
            self.log_sync_action("备份到ClawCloud", "失败", str(e))
            logger.error(f"备份失败: {e}")
            return False
    
    def restore_from_clawcloud(self):
        """从ClawCloud恢复到主数据库 - 紧急禁用版本"""
        self.log_sync_action("从ClawCloud恢复", "失败", "恢复功能已紧急禁用，防止数据丢失")
        logger.error("恢复功能已紧急禁用：TRUNCATE CASCADE操作过于危险")
        return False

        # 原始代码已注释，防止意外执行
        # 危险代码已注释 - TRUNCATE CASCADE会清空所有数据
        # 原始恢复代码已被注释，因为使用了危险的TRUNCATE CASCADE操作
        """
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

            # 获取要恢复的表（正确的依赖顺序）
            tables_to_restore = [
                # 第一阶段：基础表（无外键依赖）
                'roles', 'tags',
                # 第二阶段：用户和活动表
                'users', 'activities',
                # 第三阶段：关联表（有外键依赖）
                'activity_tags', 'user_tags', 'system_logs',
                # 第四阶段：会话和消息表
                'ai_chat_session', 'ai_chat_message',
                # 第五阶段：其他依赖表
                'activity_registrations', 'checkin_records', 'messages', 'notifications'
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

                        # 清空主表（使用TRUNCATE CASCADE处理外键约束）
                        try:
                            primary_conn.execute(text(f'TRUNCATE TABLE "{table_name}" CASCADE'))
                        except Exception as truncate_error:
                            # 如果TRUNCATE失败，尝试DELETE
                            self.log_sync_action(f"TRUNCATE {table_name} 失败，尝试DELETE", "警告", str(truncate_error))
                            primary_conn.execute(text(f'DELETE FROM "{table_name}"'))
                        primary_conn.commit()

                        # 获取备份表数据
                        result = backup_conn.execute(text(f'SELECT * FROM "{table_name}"'))
                        rows = result.fetchall()

                        if rows:
                            # 获取列名
                            columns = result.keys()
                            column_names = ', '.join([f'"{col}"' for col in columns])

                            # 使用批量插入优化恢复性能
                            self._batch_insert_fallback(primary_conn, table_name, columns, column_names, rows)

                        primary_conn.commit()
                        restored_tables += 1
                        total_rows += len(rows)
                        self.log_sync_action(f"恢复表 {table_name}", "成功", f"{len(rows)} 行数据")

                    except Exception as e:
                        self.log_sync_action(f"恢复表 {table_name}", "失败", str(e))
                        # 继续处理下一个表，不中断整个过程
                        continue

            if restored_tables > 0:
                self.log_sync_action("从ClawCloud恢复", "成功",
                                   f"恢复了 {restored_tables} 个表，共 {total_rows} 行数据")
                return True
            else:
                self.log_sync_action("从ClawCloud恢复", "失败",
                                   "没有成功恢复任何表，请检查数据库连接和权限")
                return False

        except Exception as e:
            self.log_sync_action("从ClawCloud恢复", "失败", str(e))
            logger.error(f"恢复失败: {e}")
            return False
        """

    def safe_restore_from_clawcloud(self):
        """安全的从ClawCloud恢复到主数据库 - 简化版本"""
        try:
            self.log_sync_action("安全恢复", "暂停", "恢复功能暂时禁用，防止数据丢失风险")
            logger.info("安全恢复功能被调用，但已暂时禁用")
            return False
        except Exception as e:
            logger.error(f"安全恢复方法调用失败: {e}")
            return False

    def _batch_insert_fallback(self, conn, table_name, columns, column_names, rows):
        """批量插入的优化方法"""
        if not rows:
            return

        # 根据数据量调整批次大小
        if len(rows) > 1000:
            batch_size = 1000  # 大数据集使用更大批次
        else:
            batch_size = len(rows)  # 小数据集一次性插入

        total_batches = (len(rows) + batch_size - 1) // batch_size

        for batch_num, i in enumerate(range(0, len(rows), batch_size), 1):
            batch_rows = rows[i:i + batch_size]

            try:
                # 使用executemany进行批量插入
                placeholders = ', '.join([f':{col}' for col in columns])
                insert_sql = f'INSERT INTO "{table_name}" ({column_names}) VALUES ({placeholders})'

                # 准备批量参数
                batch_params = []
                for row in batch_rows:
                    params = {col: row[j] for j, col in enumerate(columns)}
                    batch_params.append(params)

                # 执行批量插入
                conn.execute(text(insert_sql), batch_params)

                # 只在最后一批或每10批提交一次，减少提交频率
                if batch_num == total_batches or batch_num % 10 == 0:
                    conn.commit()

            except Exception as e:
                # 批量插入失败时，尝试逐行插入
                self.log_sync_action(f"批量插入 {table_name} 失败，尝试逐行插入", "警告", str(e))
                for row in batch_rows:
                    try:
                        params = {col: row[j] for j, col in enumerate(columns)}
                        conn.execute(text(insert_sql), params)
                    except Exception as row_error:
                        self.log_sync_action(f"跳过 {table_name} 中的问题行", "警告", str(row_error))
                        continue
                conn.commit()

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
