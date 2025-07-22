#!/usr/bin/env python3
"""
项目清理脚本
删除不必要的文件和目录，减少部署包大小
"""
import os
import shutil
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 要删除的文件列表
FILES_TO_DELETE = [
    # 测试和调试文件
    'debug_messages.py',
    'test.html',
    'doppler-effect.html',
    'doppler_server.py',
    'download_images.py',
    'restart.txt',
    'tencent5668923388243771053.txt',
    
    # 创建测试数据的脚本
    'create_test_activity.py',
    'create_test_activity_simple.py',
    'create_test_message.py',
    'create_simple_admin.py',
    'create_stuart_admin.py',
    'create_ai_preferences.py',
    
    # 旧的数据库重置脚本（保留final_reset.py）
    'reset_db.py',
    'reset_db_auto.py',
    'reset_db_fix.py',
    'reset_render_db.py',
    'reset_render_db_auto.py',
    'reset_render_db_with_credentials.py',
    'restore_original_db.py',
    'reset_admin_password.py',
    'reset_user_password.py',
    
    # 旧的数据库迁移脚本
    'init_db.py',
    'initialize_postgres.py',
    'migrate_to_postgres.py',
    'update_config_postgres.py',
    'update_db_schema.py',
    'update_postgres_schema.py',
    'update_sqlalchemy_queries.py',
    'set_beijing_time_final.py',
    
    # 文档文件（保留主要的README.md）
    'README_CHAT_UPDATES.md',
    'README_DATABASE_UPDATE.md',
    'README_DEPLOY.md',
    'README_RESET_DB.md',
    'README_TIMEZONE_FIX.md',
    'DEPLOY_CHECKLIST.md',
    'postgres_model_changes.md',
    'sqlalchemy_migration_summary.md',
    'sqlalchemy_migration_summary_final.md',
    
    # 修复相关的文档
    'fix_activity_registration_csrf.md',
    'fix_admin_tags_display_datetime.md',
    'fix_csrf_compatibility.md',
    'fix_csrf_compatibility_summary.md',
    'fix_csrf_timing_summary.md',
    'fix_datetime_comparison_summary.md',
    'fix_sqlalchemy_pagination_summary.md',
    'fix_summary.md',
    'fix_summary_final.md',
    'fix_summary_update.md',
    'fix_tags_selection_summary.md',
]

# 要删除的目录列表
DIRECTORIES_TO_DELETE = [
    'backend',  # 旧的后端目录
    'frontend',  # 旧的前端目录
    'models',  # 旧的模型目录
    'render_deploy',  # 旧的部署配置
    '~',  # 临时目录
]

# 要删除的scripts目录中的文件
SCRIPTS_TO_DELETE = [
    # SQLite相关的脚本（现在主要使用PostgreSQL）
    'add_checkin_manual_toggle_sqlite.sql',
    'add_points_history_cascade_sqlite.sql',
    'fix_sqlite_db.sql',
    'reset_sqlite_db.sql',
    
    # 旧的修复脚本
    'fix_checkin_key_expires.py',
    'fix_sqlalchemy_pagination.py',
    'fix_sqlalchemy_pagination.sql',
    'apply_timezone_fix.py',
    
    # 一次性的数据库更新脚本
    'add_activity_type.sql',
    'add_ai_chat_tables.sql',
    'add_ai_chat_user_index.sql',
    'add_checkin_fields.sql',
    'add_checkin_manual_toggle.sql',
    'add_completed_at_field.sql',
    'add_messaging_system.sql',
    'add_messaging_system_postgres.sql',
    'add_missing_fields.py',
    'add_points_history_cascade.sql',
    'add_points_history_cascade_postgres.sql',
    'add_poster_data_columns.sql',
    'add_poster_image_column.sql',
    'add_user_active_column.sql',
    'add_completed_at_field.sql',
    'fix_db_relations.sql',
    'fix_postgres_timezone.sql',
    'reset_db.sql',
    'reset_render_password.sql',
    'update_checkin_key_expires.sql',
    'update_render_postgres.sql',
    'update_render_postgres_activity_type.sql',
]

def cleanup_files():
    """清理文件"""
    logger.info("开始清理项目文件...")
    
    deleted_count = 0
    
    # 删除根目录中的文件
    for filename in FILES_TO_DELETE:
        if os.path.exists(filename):
            try:
                os.remove(filename)
                logger.info(f"已删除文件: {filename}")
                deleted_count += 1
            except Exception as e:
                logger.error(f"删除文件 {filename} 失败: {e}")
        else:
            logger.debug(f"文件不存在: {filename}")
    
    # 删除目录
    for dirname in DIRECTORIES_TO_DELETE:
        if os.path.exists(dirname):
            try:
                shutil.rmtree(dirname)
                logger.info(f"已删除目录: {dirname}")
                deleted_count += 1
            except Exception as e:
                logger.error(f"删除目录 {dirname} 失败: {e}")
        else:
            logger.debug(f"目录不存在: {dirname}")
    
    # 删除scripts目录中的文件
    scripts_dir = 'scripts'
    if os.path.exists(scripts_dir):
        for filename in SCRIPTS_TO_DELETE:
            filepath = os.path.join(scripts_dir, filename)
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    logger.info(f"已删除脚本: {filepath}")
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"删除脚本 {filepath} 失败: {e}")
            else:
                logger.debug(f"脚本不存在: {filepath}")
    
    logger.info(f"清理完成，共删除 {deleted_count} 个文件/目录")

def create_gitignore_additions():
    """创建.gitignore补充内容"""
    gitignore_additions = """
# 清理后不需要的文件类型
*.log
*.tmp
*.bak
*.swp
*~

# 数据库文件
*.db
*.sqlite
*.sqlite3

# 临时文件
temp_*
backup_*
restore_*

# 同步日志
sync_log_*.json
sync_scheduler.log

# 环境变量文件（如果包含敏感信息）
.env.local
.env.production
"""
    
    gitignore_path = '.gitignore'
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否已经包含这些规则
        if '# 清理后不需要的文件类型' not in content:
            with open(gitignore_path, 'a', encoding='utf-8') as f:
                f.write(gitignore_additions)
            logger.info("已更新 .gitignore 文件")
        else:
            logger.info(".gitignore 文件已包含清理规则")
    else:
        with open(gitignore_path, 'w', encoding='utf-8') as f:
            f.write(gitignore_additions.strip())
        logger.info("已创建 .gitignore 文件")

def show_remaining_files():
    """显示清理后剩余的重要文件"""
    important_files = [
        'src/',
        'scripts/auto_sync.py',
        'scripts/ensure_db_structure.py',
        'requirements.txt',
        'Procfile',
        'gunicorn_config.py',
        'wsgi.py',
        'final_reset.py',
        'create_admin.py',
        'README.md',
        '.gitignore'
    ]
    
    logger.info("清理后保留的重要文件/目录:")
    for item in important_files:
        if os.path.exists(item):
            logger.info(f"  ✓ {item}")
        else:
            logger.warning(f"  ✗ {item} (不存在)")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='项目清理工具')
    parser.add_argument('--dry-run', action='store_true', help='仅显示将要删除的文件，不实际删除')
    parser.add_argument('--force', action='store_true', help='强制删除，不询问确认')
    
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("DRY RUN 模式 - 仅显示将要删除的文件:")
        logger.info("文件:")
        for f in FILES_TO_DELETE:
            if os.path.exists(f):
                logger.info(f"  - {f}")
        logger.info("目录:")
        for d in DIRECTORIES_TO_DELETE:
            if os.path.exists(d):
                logger.info(f"  - {d}/")
        logger.info("脚本:")
        for s in SCRIPTS_TO_DELETE:
            script_path = os.path.join('scripts', s)
            if os.path.exists(script_path):
                logger.info(f"  - {script_path}")
        return
    
    if not args.force:
        response = input("确定要清理项目文件吗？这将删除许多文件和目录。(y/N): ")
        if response.lower() != 'y':
            logger.info("清理操作已取消")
            return
    
    cleanup_files()
    create_gitignore_additions()
    show_remaining_files()
    
    logger.info("项目清理完成！")
    logger.info("建议运行 'git add .' 和 'git commit' 来提交更改")

if __name__ == '__main__':
    main()
