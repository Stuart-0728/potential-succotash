import os
import re
import sys
import shutil
from datetime import datetime

def fix_csrf_compatibility():
    """修复Flask-WTF版本兼容问题，替换csrf_exempt为兼容方式"""
    print("开始修复CSRF兼容性问题...")
    
    # 1. 备份education.py
    education_file = os.path.join('src', 'routes', 'education.py')
    backup_file = f"{education_file}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        shutil.copy2(education_file, backup_file)
        print(f"  - 已备份education.py到 {backup_file}")
    except Exception as e:
        print(f"  - 备份文件失败: {e}")
    
    # 2. 修复education.py中的csrf_exempt导入和使用
    try:
        with open(education_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否包含错误导入
        if 'csrf_exempt' in content:
            # 替换导入语句
            modified = re.sub(
                r'from flask_wtf\.csrf import CSRFProtect, generate_csrf, csrf_exempt',
                'from flask_wtf.csrf import CSRFProtect, generate_csrf',
                content
            )
            
            # 删除@csrf_exempt装饰器
            modified = re.sub(
                r'@csrf_exempt\s*\n',
                '',
                modified
            )
            
            # 写回文件
            with open(education_file, 'w', encoding='utf-8') as f:
                f.write(modified)
                
            print("  - 已修复education.py文件中的csrf_exempt导入和使用")
        else:
            print("  - education.py文件中未找到csrf_exempt，无需修改")
    except Exception as e:
        print(f"  - 修改education.py文件失败: {e}")
    
    # 3. 备份__init__.py
    init_file = os.path.join('src', '__init__.py')
    init_backup = f"{init_file}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        shutil.copy2(init_file, init_backup)
        print(f"  - 已备份__init__.py到 {init_backup}")
    except Exception as e:
        print(f"  - 备份__init__.py文件失败: {e}")
    
    # 4. 修复__init__.py文件，添加CSRF豁免配置
    try:
        with open(init_file, 'r', encoding='utf-8') as f:
            init_content = f.read()
        
        # 检查CSRF初始化位置
        match = re.search(r'register_blueprints\(app\)', init_content)
        if match:
            # 在register_blueprints之前添加CSRF豁免配置
            blueprint_pos = match.start()
            prefix = init_content[:blueprint_pos]
            suffix = init_content[blueprint_pos:]
            
            csrf_exempt_code = """    # 添加特定API路由的CSRF豁免
    with app.app_context():
        from src.routes.education import education_bp
        # 豁免/education/api/gemini路由的CSRF保护
        app.view_functions[education_bp.name + '.gemini_api']._csrf_exempt = True
        app.logger.info('已为/education/api/gemini路由添加CSRF豁免')
    
    """
            
            modified_init = prefix + csrf_exempt_code + suffix
            
            # 写回文件
            with open(init_file, 'w', encoding='utf-8') as f:
                f.write(modified_init)
                
            print("  - 已在__init__.py中添加CSRF豁免配置")
        else:
            print("  - 无法在__init__.py中找到register_blueprints位置，请手动添加CSRF豁免配置")
    except Exception as e:
        print(f"  - 修改__init__.py文件失败: {e}")

    print("CSRF兼容性修复完成")

if __name__ == "__main__":
    fix_csrf_compatibility() 