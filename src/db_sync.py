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
        """将主数据库备份到ClawCloud"""
        if not self.dual_db.is_dual_db_enabled():
            self.log_sync_action("备份到ClawCloud", "失败", "双数据库未配置")
            return False
        
        try:
            # 1. 从主数据库导出数据
            self.log_sync_action("导出主数据库", "开始")
            
            # 使用pg_dump导出主数据库
            primary_url = self.dual_db.primary_db_url
            backup_file = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
            
            # 解析数据库URL
            import urllib.parse
            parsed = urllib.parse.urlparse(primary_url)
            
            # 设置环境变量
            env = os.environ.copy()
            env['PGPASSWORD'] = parsed.password
            
            # 执行pg_dump
            dump_cmd = [
                'pg_dump',
                '-h', parsed.hostname,
                '-p', str(parsed.port or 5432),
                '-U', parsed.username,
                '-d', parsed.path[1:],  # 移除开头的'/'
                '--no-owner',
                '--no-privileges',
                '--clean',
                '--if-exists',
                '-f', backup_file
            ]
            
            result = subprocess.run(dump_cmd, env=env, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.log_sync_action("导出主数据库", "失败", result.stderr)
                return False
            
            self.log_sync_action("导出主数据库", "成功", f"备份文件: {backup_file}")
            
            # 2. 导入到备份数据库
            self.log_sync_action("导入到备份数据库", "开始")
            
            backup_url = self.dual_db.backup_db_url
            backup_parsed = urllib.parse.urlparse(backup_url)
            
            env['PGPASSWORD'] = backup_parsed.password
            
            # 执行psql导入
            import_cmd = [
                'psql',
                '-h', backup_parsed.hostname,
                '-p', str(backup_parsed.port or 5432),
                '-U', backup_parsed.username,
                '-d', backup_parsed.path[1:],
                '-f', backup_file
            ]
            
            result = subprocess.run(import_cmd, env=env, capture_output=True, text=True)
            
            # 清理备份文件
            if os.path.exists(backup_file):
                os.remove(backup_file)
            
            if result.returncode != 0:
                self.log_sync_action("导入到备份数据库", "失败", result.stderr)
                return False
            
            self.log_sync_action("导入到备份数据库", "成功")
            self.log_sync_action("完整备份", "成功", "数据已成功同步到ClawCloud")
            
            return True
            
        except Exception as e:
            self.log_sync_action("备份到ClawCloud", "失败", str(e))
            return False
    
    def restore_from_clawcloud(self):
        """从ClawCloud恢复到主数据库"""
        if not self.dual_db.is_dual_db_enabled():
            self.log_sync_action("从ClawCloud恢复", "失败", "双数据库未配置")
            return False
        
        try:
            # 1. 从备份数据库导出数据
            self.log_sync_action("导出备份数据库", "开始")
            
            backup_url = self.dual_db.backup_db_url
            backup_file = f"restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
            
            # 解析数据库URL
            import urllib.parse
            parsed = urllib.parse.urlparse(backup_url)
            
            # 设置环境变量
            env = os.environ.copy()
            env['PGPASSWORD'] = parsed.password
            
            # 执行pg_dump
            dump_cmd = [
                'pg_dump',
                '-h', parsed.hostname,
                '-p', str(parsed.port or 5432),
                '-U', parsed.username,
                '-d', parsed.path[1:],
                '--no-owner',
                '--no-privileges',
                '--clean',
                '--if-exists',
                '-f', backup_file
            ]
            
            result = subprocess.run(dump_cmd, env=env, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.log_sync_action("导出备份数据库", "失败", result.stderr)
                return False
            
            self.log_sync_action("导出备份数据库", "成功")
            
            # 2. 导入到主数据库
            self.log_sync_action("导入到主数据库", "开始")
            
            primary_url = self.dual_db.primary_db_url
            primary_parsed = urllib.parse.urlparse(primary_url)
            
            env['PGPASSWORD'] = primary_parsed.password
            
            # 执行psql导入
            import_cmd = [
                'psql',
                '-h', primary_parsed.hostname,
                '-p', str(primary_parsed.port or 5432),
                '-U', primary_parsed.username,
                '-d', primary_parsed.path[1:],
                '-f', backup_file
            ]
            
            result = subprocess.run(import_cmd, env=env, capture_output=True, text=True)
            
            # 清理备份文件
            if os.path.exists(backup_file):
                os.remove(backup_file)
            
            if result.returncode != 0:
                self.log_sync_action("导入到主数据库", "失败", result.stderr)
                return False
            
            self.log_sync_action("导入到主数据库", "成功")
            self.log_sync_action("完整恢复", "成功", "数据已从ClawCloud恢复到主数据库")
            
            return True
            
        except Exception as e:
            self.log_sync_action("从ClawCloud恢复", "失败", str(e))
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
