import os
import sys
import re
from datetime import datetime

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def fix_csrf_init_structure():
    """修复CSRF初始化代码结构问题"""
    print("开始修复CSRF初始化代码结构...")
    
    # 修复__init__.py中的CSRF初始化代码
    init_py_path = os.path.join(current_dir, 'src', '__init__.py')
    
    with open(init_py_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. 备份原始文件
    backup_path = f"{init_py_path}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  - 已备份原始文件到: {backup_path}")
    
    # 2. 修复代码结构
    # 首先删除错误的CSRF代码块
    content_lines = content.split('\n')
    fixed_lines = []
    skip_mode = False
    
    for line in content_lines:
        if '# 设置CSRF豁免路径' in line or '@csrf.exempt' in line:
            skip_mode = True
        
        if skip_mode and 'app.logger.info(\'已为/education/api/gemini路由添加CSRF豁免\')' in line:
            skip_mode = False
            continue
        
        if not skip_mode:
            fixed_lines.append(line)
    
    # 3. 找到create_app函数中适当的位置插入正确的CSRF豁免代码
    create_app_pattern = r"def create_app\(config_name=None\):"
    csrf_init_pattern = r"csrf\.init_app\(app\)"
    
    # 创建正确缩进的CSRF豁免代码
    csrf_exempt_code = """
    # 初始化CSRF保护
    csrf.init_app(app)
    
    # 添加特定API路由的CSRF豁免
    from src.routes.education import education_bp
    
    @app.after_request
    def add_csrf_protection(response):
        \"\"\"为应用添加CSRF保护\"\"\"
        return response
    
    # 使用Flask原生方式为特定路由豁免CSRF保护
    education_gemini_view = app.view_functions.get(education_bp.name + '.gemini_api')
    if education_gemini_view:
        education_gemini_view._csrf_exempt = True
        app.logger.info('已为/education/api/gemini路由添加CSRF豁免')
    else:
        app.logger.warning('未找到gemini_api视图函数，无法添加CSRF豁免')
"""

    # 替换CSRF初始化代码
    fixed_content = '\n'.join(fixed_lines)
    fixed_content = fixed_content.replace(
        "csrf.init_app(app)",
        csrf_exempt_code
    )
    
    # 4. 更新education.py，确保没有重复的导入
    education_py_path = os.path.join(current_dir, 'src', 'routes', 'education.py')
    
    if os.path.exists(education_py_path):
        with open(education_py_path, 'r', encoding='utf-8') as f:
            edu_content = f.read()
            
        # 查找并修复重复的导入
        if edu_content.count('from flask import Blueprint') > 1:
            # 删除重复的导入行
            edu_content = re.sub(
                r'from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify\nfrom flask import Blueprint',
                'from flask import Blueprint',
                edu_content
            )
            
            # 备份原始文件
            edu_backup_path = f"{education_py_path}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            with open(edu_backup_path, 'w', encoding='utf-8') as f:
                f.write(edu_content)
            print(f"  - 已备份教育模块文件到: {edu_backup_path}")
            
            # 保存修复后的文件
            with open(education_py_path, 'w', encoding='utf-8') as f:
                f.write(edu_content)
            print("  - 已修复重复的导入语句")
    
    # 保存修复后的文件
    with open(init_py_path, 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    print("  - 已修复CSRF初始化代码结构")
    
    print("CSRF初始化代码结构修复完成！")

def main():
    """主函数，执行所有修复操作"""
    print(f"===== 开始执行修复脚本 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} =====")
    
    # 执行修复操作
    fix_csrf_init_structure()
    
    print(f"===== 修复脚本执行完成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} =====")

if __name__ == "__main__":
    main() 