#!/usr/bin/env python3
"""
自动数据库同步脚本
定期将主数据库备份到ClawCloud
"""
import os
import sys
import time
import logging
import schedule
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.db_sync import DatabaseSyncer
from src.dual_db_config import dual_db

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sync_scheduler.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class AutoSyncScheduler:
    """自动同步调度器"""
    
    def __init__(self):
        self.syncer = DatabaseSyncer()
        self.last_sync_time = None
        self.sync_interval_hours = int(os.environ.get('SYNC_INTERVAL_HOURS', 6))  # 默认6小时同步一次
        self.max_retries = 3
        
    def sync_job(self):
        """执行同步任务"""
        logger.info("开始执行定时同步任务")
        
        # 检查双数据库是否配置
        if not dual_db.is_dual_db_enabled():
            logger.warning("双数据库未配置，跳过同步")
            return
        
        # 检查数据库连接
        db_info = dual_db.get_database_info()
        if not db_info['primary']:
            logger.error("主数据库连接失败，跳过同步")
            return
        
        if not db_info['backup']:
            logger.error("备份数据库连接失败，跳过同步")
            return
        
        # 执行同步
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                success = self.syncer.backup_to_clawcloud()
                if success:
                    self.last_sync_time = datetime.now()
                    logger.info(f"同步成功完成，下次同步时间: {self.last_sync_time + timedelta(hours=self.sync_interval_hours)}")
                    break
                else:
                    retry_count += 1
                    logger.warning(f"同步失败，重试 {retry_count}/{self.max_retries}")
                    if retry_count < self.max_retries:
                        time.sleep(60)  # 等待1分钟后重试
            except Exception as e:
                retry_count += 1
                logger.error(f"同步过程中出错: {e}，重试 {retry_count}/{self.max_retries}")
                if retry_count < self.max_retries:
                    time.sleep(60)
        
        if retry_count >= self.max_retries:
            logger.error("同步失败，已达到最大重试次数")
    
    def health_check(self):
        """健康检查"""
        logger.info("执行健康检查")
        
        try:
            db_info = dual_db.get_database_info()
            
            # 记录数据库状态
            primary_status = "正常" if db_info['primary'] else "异常"
            backup_status = "正常" if db_info['backup'] else "异常"
            
            logger.info(f"主数据库状态: {primary_status}")
            logger.info(f"备份数据库状态: {backup_status}")
            
            if db_info['primary_latency']:
                logger.info(f"主数据库延迟: {db_info['primary_latency']:.2f}ms")
            
            if db_info['backup_latency']:
                logger.info(f"备份数据库延迟: {db_info['backup_latency']:.2f}ms")
            
            # 检查上次同步时间
            if self.last_sync_time:
                time_since_sync = datetime.now() - self.last_sync_time
                hours_since_sync = time_since_sync.total_seconds() / 3600
                
                if hours_since_sync > self.sync_interval_hours * 2:
                    logger.warning(f"距离上次同步已过去 {hours_since_sync:.1f} 小时，可能存在问题")
                else:
                    logger.info(f"距离上次同步: {hours_since_sync:.1f} 小时")
            else:
                logger.info("尚未执行过同步")
                
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
    
    def start_scheduler(self):
        """启动调度器"""
        logger.info(f"启动自动同步调度器，同步间隔: {self.sync_interval_hours} 小时")
        
        # 设置定时任务
        schedule.every(self.sync_interval_hours).hours.do(self.sync_job)
        schedule.every(30).minutes.do(self.health_check)  # 每30分钟执行一次健康检查
        
        # 立即执行一次健康检查
        self.health_check()
        
        # 如果启用了立即同步，执行一次同步
        if os.environ.get('IMMEDIATE_SYNC', 'false').lower() == 'true':
            logger.info("执行立即同步")
            self.sync_job()
        
        # 运行调度器
        logger.info("调度器已启动，等待任务执行...")
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
            except KeyboardInterrupt:
                logger.info("收到中断信号，停止调度器")
                break
            except Exception as e:
                logger.error(f"调度器运行出错: {e}")
                time.sleep(60)

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='自动数据库同步调度器')
    parser.add_argument('--sync-now', action='store_true', help='立即执行一次同步')
    parser.add_argument('--health-check', action='store_true', help='执行健康检查')
    parser.add_argument('--daemon', action='store_true', help='以守护进程模式运行')
    
    args = parser.parse_args()
    
    scheduler = AutoSyncScheduler()
    
    if args.sync_now:
        logger.info("执行立即同步")
        scheduler.sync_job()
    elif args.health_check:
        logger.info("执行健康检查")
        scheduler.health_check()
    elif args.daemon:
        logger.info("以守护进程模式启动")
        scheduler.start_scheduler()
    else:
        print("使用方法:")
        print("  python auto_sync.py --sync-now      # 立即执行同步")
        print("  python auto_sync.py --health-check  # 执行健康检查")
        print("  python auto_sync.py --daemon        # 以守护进程模式运行")

if __name__ == '__main__':
    main()
