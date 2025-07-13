#!/usr/bin/env python
import os
import re
import sys
from pathlib import Path

def update_file(file_path):
    """更新单个文件中的SQLAlchemy查询语法"""
    print(f"处理文件: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 保存原始内容，用于比较是否有变化
    original_content = content
    
    # 1. 替换 Model.query.get(id) 为 db.session.get(Model, id)
    content = re.sub(r'([A-Za-z_][A-Za-z0-9_]*?)\.query\.get\(([^)]+?)\)', r'db.session.get(\1, \2)', content)
    
    # 2. 替换 Model.query.get_or_404(id) 为 db.get_or_404(Model, id)
    content = re.sub(r'([A-Za-z_][A-Za-z0-9_]*?)\.query\.get_or_404\(([^)]+?)\)', r'db.get_or_404(\1, \2)', content)
    
    # 3. 替换 Model.query.filter_by(...).first() 为 db.session.execute(db.select(Model).filter_by(...)).scalar_one_or_none()
    content = re.sub(
        r'([A-Za-z_][A-Za-z0-9_]*?)\.query\.filter_by\(([^)]+?)\)\.first\(\)',
        r'db.session.execute(db.select(\1).filter_by(\2)).scalar_one_or_none()',
        content
    )
    
    # 4. 替换 Model.query.filter(...).first() 为 db.session.execute(db.select(Model).filter(...)).scalar_one_or_none()
    content = re.sub(
        r'([A-Za-z_][A-Za-z0-9_]*?)\.query\.filter\(([^)]+?)\)\.first\(\)',
        r'db.session.execute(db.select(\1).filter(\2)).scalar_one_or_none()',
        content
    )
    
    # 5. 替换 Model.query.filter_by(...).all() 为 db.session.execute(db.select(Model).filter_by(...)).scalars().all()
    content = re.sub(
        r'([A-Za-z_][A-Za-z0-9_]*?)\.query\.filter_by\(([^)]+?)\)\.all\(\)',
        r'db.session.execute(db.select(\1).filter_by(\2)).scalars().all()',
        content
    )
    
    # 6. 替换 Model.query.filter(...).all() 为 db.session.execute(db.select(Model).filter(...)).scalars().all()
    content = re.sub(
        r'([A-Za-z_][A-Za-z0-9_]*?)\.query\.filter\(([^)]+?)\)\.all\(\)',
        r'db.session.execute(db.select(\1).filter(\2)).scalars().all()',
        content
    )
    
    # 7. 替换 Model.query.all() 为 db.session.execute(db.select(Model)).scalars().all()
    content = re.sub(
        r'([A-Za-z_][A-Za-z0-9_]*?)\.query\.all\(\)',
        r'db.session.execute(db.select(\1)).scalars().all()',
        content
    )
    
    # 8. 替换 Model.query.filter_by(...).count() 为 db.session.execute(db.select(func.count()).select_from(Model).filter_by(...)).scalar()
    content = re.sub(
        r'([A-Za-z_][A-Za-z0-9_]*?)\.query\.filter_by\(([^)]+?)\)\.count\(\)',
        r'db.session.execute(db.select(func.count()).select_from(\1).filter_by(\2)).scalar()',
        content
    )
    
    # 9. 替换 Model.query.filter(...).count() 为 db.session.execute(db.select(func.count()).select_from(Model).filter(...)).scalar()
    content = re.sub(
        r'([A-Za-z_][A-Za-z0-9_]*?)\.query\.filter\(([^)]+?)\)\.count\(\)',
        r'db.session.execute(db.select(func.count()).select_from(\1).filter(\2)).scalar()',
        content
    )
    
    # 10. 替换 Model.query.count() 为 db.session.execute(db.select(func.count()).select_from(Model)).scalar()
    content = re.sub(
        r'([A-Za-z_][A-Za-z0-9_]*?)\.query\.count\(\)',
        r'db.session.execute(db.select(func.count()).select_from(\1)).scalar()',
        content
    )
    
    # 11. 替换 Model.query.order_by(...).all() 为 db.session.execute(db.select(Model).order_by(...)).scalars().all()
    content = re.sub(
        r'([A-Za-z_][A-Za-z0-9_]*?)\.query\.order_by\(([^)]+?)\)\.all\(\)',
        r'db.session.execute(db.select(\1).order_by(\2)).scalars().all()',
        content
    )
    
    # 12. 替换 Model.query.order_by(...).first() 为 db.session.execute(db.select(Model).order_by(...)).scalar_one_or_none()
    content = re.sub(
        r'([A-Za-z_][A-Za-z0-9_]*?)\.query\.order_by\(([^)]+?)\)\.first\(\)',
        r'db.session.execute(db.select(\1).order_by(\2)).scalar_one_or_none()',
        content
    )
    
    # 13. 替换 Model.query.order_by(...).limit(...).all() 为 db.session.execute(db.select(Model).order_by(...).limit(...)).scalars().all()
    content = re.sub(
        r'([A-Za-z_][A-Za-z0-9_]*?)\.query\.order_by\(([^)]+?)\)\.limit\(([^)]+?)\)\.all\(\)',
        r'db.session.execute(db.select(\1).order_by(\2).limit(\3)).scalars().all()',
        content
    )
    
    # 14. 替换 Model.query.paginate(...) 为 db.paginate(db.select(Model), ...)
    content = re.sub(
        r'([A-Za-z_][A-Za-z0-9_]*?)\.query\.paginate\(([^)]+?)\)',
        r'db.paginate(db.select(\1), \2)',
        content
    )
    
    # 15. 替换 Model.query.filter_by(...).paginate(...) 为 db.paginate(db.select(Model).filter_by(...), ...)
    content = re.sub(
        r'([A-Za-z_][A-Za-z0-9_]*?)\.query\.filter_by\(([^)]+?)\)\.paginate\(([^)]+?)\)',
        r'db.paginate(db.select(\1).filter_by(\2), \3)',
        content
    )
    
    # 16. 替换 Model.query.filter(...).paginate(...) 为 db.paginate(db.select(Model).filter(...), ...)
    content = re.sub(
        r'([A-Za-z_][A-Za-z0-9_]*?)\.query\.filter\(([^)]+?)\)\.paginate\(([^)]+?)\)',
        r'db.paginate(db.select(\1).filter(\2), \3)',
        content
    )
    
    # 17. 替换 Model.query.filter_by(...).order_by(...).paginate(...) 为 db.paginate(db.select(Model).filter_by(...).order_by(...), ...)
    content = re.sub(
        r'([A-Za-z_][A-Za-z0-9_]*?)\.query\.filter_by\(([^)]+?)\)\.order_by\(([^)]+?)\)\.paginate\(([^)]+?)\)',
        r'db.paginate(db.select(\1).filter_by(\2).order_by(\3), \4)',
        content
    )
    
    # 18. 替换 Model.query.filter(...).order_by(...).paginate(...) 为 db.paginate(db.select(Model).filter(...).order_by(...), ...)
    content = re.sub(
        r'([A-Za-z_][A-Za-z0-9_]*?)\.query\.filter\(([^)]+?)\)\.order_by\(([^)]+?)\)\.paginate\(([^)]+?)\)',
        r'db.paginate(db.select(\1).filter(\2).order_by(\3), \4)',
        content
    )
    
    # 19. 替换 Model.query.order_by(...).paginate(...) 为 db.paginate(db.select(Model).order_by(...), ...)
    content = re.sub(
        r'([A-Za-z_][A-Za-z0-9_]*?)\.query\.order_by\(([^)]+?)\)\.paginate\(([^)]+?)\)',
        r'db.paginate(db.select(\1).order_by(\2), \3)',
        content
    )
    
    # 检查是否有变化
    if content != original_content:
        # 备份原文件
        backup_path = f"{file_path}.bak"
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(original_content)
        
        # 写入更新后的内容
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"  已更新并备份到 {backup_path}")
        return True
    else:
        print("  没有需要更新的查询")
        return False

def update_directory(directory):
    """更新目录中所有Python文件的SQLAlchemy查询语法"""
    updated_files = 0
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                if update_file(file_path):
                    updated_files += 1
    
    return updated_files

def main():
    """主函数"""
    if len(sys.argv) > 1:
        target = sys.argv[1]
        if os.path.isfile(target) and target.endswith('.py'):
            update_file(target)
        elif os.path.isdir(target):
            updated_files = update_directory(target)
            print(f"共更新了 {updated_files} 个文件")
        else:
            print(f"错误: {target} 不是有效的Python文件或目录")
            sys.exit(1)
    else:
        # 默认更新当前目录和src目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        src_dir = os.path.join(current_dir, 'src')
        
        updated_files = 0
        
        # 更新根目录下的Python文件
        for file in os.listdir(current_dir):
            if file.endswith('.py') and file != os.path.basename(__file__):
                file_path = os.path.join(current_dir, file)
                if update_file(file_path):
                    updated_files += 1
        
        # 更新src目录
        if os.path.exists(src_dir) and os.path.isdir(src_dir):
            updated_files += update_directory(src_dir)
        
        print(f"共更新了 {updated_files} 个文件")

if __name__ == '__main__':
    main() 