"""
双数据库配置模块
支持Render PostgreSQL作为主库，ClawCloud作为备份库
"""
import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class DualDatabaseConfig:
    """双数据库配置类"""
    
    def __init__(self):
        # 主数据库配置 (Render PostgreSQL)
        self.primary_db_url = os.environ.get('DATABASE_URL') or os.environ.get('RENDER_DATABASE_URL')
        
        # 备份数据库配置 (ClawCloud)
        self.backup_db_url = os.environ.get('BACKUP_DATABASE_URL') or os.environ.get('CLAWCLOUD_DATABASE_URL')
        
        # 数据库引擎
        self.primary_engine = None
        self.backup_engine = None
        
        # 会话工厂
        self.primary_session_factory = None
        self.backup_session_factory = None
        
        # 初始化数据库连接
        self._init_connections()
    
    def _init_connections(self):
        """初始化数据库连接"""
        try:
            if self.primary_db_url:
                self.primary_engine = create_engine(
                    self.primary_db_url,
                    pool_size=10,
                    max_overflow=20,
                    pool_timeout=30,
                    pool_recycle=1800,
                    pool_pre_ping=True,
                    connect_args={
                        'connect_timeout': 10,
                        'keepalives': 1,
                        'keepalives_idle': 30,
                        'keepalives_interval': 10,
                        'keepalives_count': 5,
                    }
                )
                self.primary_session_factory = sessionmaker(bind=self.primary_engine)
                logger.info("主数据库连接初始化成功")
            
            if self.backup_db_url:
                self.backup_engine = create_engine(
                    self.backup_db_url,
                    pool_size=5,
                    max_overflow=10,
                    pool_timeout=30,
                    pool_recycle=1800,
                    pool_pre_ping=True,
                    connect_args={
                        'connect_timeout': 15,
                        'keepalives': 1,
                        'keepalives_idle': 30,
                        'keepalives_interval': 10,
                        'keepalives_count': 5,
                    }
                )
                self.backup_session_factory = sessionmaker(bind=self.backup_engine)
                logger.info("备份数据库连接初始化成功")
                
        except Exception as e:
            logger.error(f"数据库连接初始化失败: {e}")
    
    def get_primary_session(self):
        """获取主数据库会话"""
        if self.primary_session_factory:
            return self.primary_session_factory()
        return None
    
    def get_backup_session(self):
        """获取备份数据库会话"""
        if self.backup_session_factory:
            return self.backup_session_factory()
        return None
    
    def test_connections(self):
        """测试数据库连接"""
        results = {
            'primary': False,
            'backup': False,
            'primary_latency': None,
            'backup_latency': None
        }
        
        # 测试主数据库
        if self.primary_engine:
            try:
                start_time = datetime.now()
                with self.primary_engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                end_time = datetime.now()
                results['primary'] = True
                results['primary_latency'] = (end_time - start_time).total_seconds() * 1000
                logger.info(f"主数据库连接正常，延迟: {results['primary_latency']:.2f}ms")
            except Exception as e:
                logger.error(f"主数据库连接失败: {e}")
        
        # 测试备份数据库
        if self.backup_engine:
            try:
                start_time = datetime.now()
                with self.backup_engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                end_time = datetime.now()
                results['backup'] = True
                results['backup_latency'] = (end_time - start_time).total_seconds() * 1000
                logger.info(f"备份数据库连接正常，延迟: {results['backup_latency']:.2f}ms")
            except Exception as e:
                logger.error(f"备份数据库连接失败: {e}")
        
        return results
    
    def get_active_database_url(self):
        """获取当前活跃的数据库URL"""
        # 优先使用主数据库
        if self.primary_db_url and self.primary_engine:
            try:
                with self.primary_engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                return self.primary_db_url
            except:
                logger.warning("主数据库不可用，尝试使用备份数据库")
        
        # 如果主数据库不可用，使用备份数据库
        if self.backup_db_url and self.backup_engine:
            try:
                with self.backup_engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                return self.backup_db_url
            except:
                logger.error("备份数据库也不可用")
        
        return self.primary_db_url or self.backup_db_url
    
    def is_dual_db_enabled(self):
        """检查是否启用了双数据库"""
        return bool(self.primary_db_url and self.backup_db_url)
    
    def get_database_info(self):
        """获取数据库信息"""
        info = {
            'dual_db_enabled': self.is_dual_db_enabled(),
            'primary_configured': bool(self.primary_db_url),
            'backup_configured': bool(self.backup_db_url),
            'active_database': 'primary' if self.primary_db_url else 'backup'
        }
        
        # 测试连接
        test_results = self.test_connections()
        info.update(test_results)
        
        return info

# 全局双数据库配置实例
dual_db = DualDatabaseConfig()
