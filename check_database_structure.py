#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
检查数据库表结构与SQLAlchemy模型定义的一致性
"""

import os
import sys
import logging
from datetime import datetime
import inspect
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm.attributes import InstrumentedAttribute

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_model_vs_db():
    """检查模型定义与数据库表结构的一致性"""
    try:
        # 导入应用
        from src import create_app, db
        from src.models import __name__ as models_module_name
        import src.models
        
        # 创建Flask应用获取数据库上下文
        app = create_app()
        
        with app.app_context():
            # 获取所有模型类
            models = {}
            for attr_name in dir(src.models):
                attr = getattr(src.models, attr_name)
                if (isinstance(attr, type) and 
                    hasattr(attr, '__tablename__') and 
                    not attr_name.startswith('_')):
                    models[attr_name] = attr
            
            logger.info(f"找到 {len(models)} 个模型类")
            
            # 检查数据库中的表
            inspector = sa_inspect(db.engine)
            db_tables = inspector.get_table_names()
            
            logger.info(f"数据库中有 {len(db_tables)} 个表")
            
            # 检查每个模型
            issues = []
            for model_name, model_class in models.items():
                table_name = model_class.__tablename__
                logger.info(f"检查模型 {model_name} (表: {table_name})")
                
                # 检查表是否存在
                if table_name not in db_tables:
                    issues.append(f"表 '{table_name}' 不存在 (模型: {model_name})")
                    continue
                
                # 获取表的列
                db_columns = {col['name']: col for col in inspector.get_columns(table_name)}
                
                # 获取模型的列
                model_columns = {}
                for attr_name, attr in inspect.getmembers(model_class):
                    if isinstance(attr, InstrumentedAttribute) and not attr_name.startswith('_'):
                        # 获取列名
                        column = attr.property.columns[0]
                        model_columns[column.name] = column
                
                # 检查列是否匹配
                for col_name, column in model_columns.items():
                    if col_name not in db_columns:
                        issues.append(f"列 '{col_name}' 在模型 {model_name} 中定义但在表 {table_name} 中不存在")
                    else:
                        # 可以进一步检查列类型等信息
                        pass
                
                # 检查数据库中有但模型中没有的列
                for col_name in db_columns:
                    if col_name not in model_columns:
                        issues.append(f"列 '{col_name}' 在表 {table_name} 中存在但在模型 {model_name} 中未定义")
            
            # 输出结果
            if issues:
                logger.warning(f"发现 {len(issues)} 个不一致问题:")
                for issue in issues:
                    logger.warning(f"  - {issue}")
                
                print("\n不一致问题:")
                for issue in issues:
                    print(f"  - {issue}")
                
                print("\n建议解决方案:")
                print("1. 使用数据库迁移工具（如Alembic）来同步模型和数据库")
                print("2. 手动编写SQL脚本修复不一致的问题")
                print("3. 确保所有模型变更都通过迁移脚本应用到数据库")
            else:
                logger.info("所有模型与数据库表结构一致")
                print("\n检查完成：所有模型与数据库表结构一致 ✓")
            
            return issues
            
    except Exception as e:
        logger.error(f"检查模型与数据库一致性时出错: {str(e)}")
        print(f"错误: {str(e)}")
        return None

if __name__ == '__main__':
    print(f"开始检查数据库结构与模型定义一致性 - {datetime.now()}")
    issues = check_model_vs_db()
    if issues is None:
        print("检查失败，请查看日志获取详细错误信息")
        sys.exit(1)
    elif issues:
        print(f"检查完成，发现 {len(issues)} 个问题")
        sys.exit(1)
    else:
        print("检查完成，没有发现问题")
        sys.exit(0) 