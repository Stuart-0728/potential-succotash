import os
import sys
import re
from datetime import datetime

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def fix_csrf_exempt_compatibility():
    """修复Flask-WTF版本兼容问题，替换csrf_exempt为兼容方式"""
    print("开始修复CSRF豁免版本兼容问题...")
    
    # 修复education.py中的csrf_exempt导入和使用
    education_py_path = os.path.join(current_dir, 'src', 'routes', 'education.py')
    
    with open(education_py_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. 备份原始文件
    backup_path = f"{education_py_path}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  - 已备份原始文件到: {backup_path}")
    
    # 2. 替换import语句
    modified_content = content.replace(
        'from flask_wtf.csrf import CSRFProtect, generate_csrf, csrf_exempt',
        'from flask_wtf.csrf import CSRFProtect, generate_csrf\nfrom flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify'
    )
    
    # 3. 删除@csrf_exempt装饰器，替换为在应用初始化时全局设置CSRF排除
    modified_content = modified_content.replace(
        '@education_bp.route(\'/api/gemini\', methods=[\'POST\'])\n@csrf_exempt',
        '@education_bp.route(\'/api/gemini\', methods=[\'POST\'])'
    )
    
    # 4. 保存修改后的文件
    with open(education_py_path, 'w', encoding='utf-8') as f:
        f.write(modified_content)
    print("  - 已移除csrf_exempt装饰器，将使用全局CSRF排除方式")
    
    # 5. 修改__init__.py，添加全局CSRF豁免设置
    init_py_path = os.path.join(current_dir, 'src', '__init__.py')
    
    with open(init_py_path, 'r', encoding='utf-8') as f:
        init_content = f.read()
    
    # 备份原始文件
    backup_init_path = f"{init_py_path}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    with open(backup_init_path, 'w', encoding='utf-8') as f:
        f.write(init_content)
    print(f"  - 已备份原始文件到: {backup_init_path}")
    
    # 添加CSRF豁免路径
    # 查找CSRFProtect实例化的位置
    csrf_pattern = r"(csrf = CSRFProtect\(\).*?csrf\.init_app\(app\))"
    
    # 如果找到了CSRF初始化代码
    if re.search(csrf_pattern, init_content, re.DOTALL):
        # 添加CSRF豁免配置
        csrf_exempt_code = (
            "csrf = CSRFProtect()\n"
            "    # 设置CSRF豁免路径\n"
            "    @csrf.exempt\n"
            "    def csrf_exempt_blueprint(blueprint):\n"
            "        return blueprint\n"
            "\n"
            "    # 初始化CSRF保护\n"
            "    csrf.init_app(app)\n"
            "    \n"
            "    # 添加特定API路由的CSRF豁免\n"
            "    from src.routes.education import education_bp\n"
            "    # 豁免/education/api/gemini路由的CSRF保护\n"
            "    app.view_functions[education_bp.name + '.gemini_api']._csrf_exempt = True\n"
            "    app.logger.info('已为/education/api/gemini路由添加CSRF豁免')"
        )
        
        modified_init_content = re.sub(csrf_pattern, csrf_exempt_code, init_content, flags=re.DOTALL)
        
        # 保存修改后的文件
        with open(init_py_path, 'w', encoding='utf-8') as f:
            f.write(modified_init_content)
        print("  - 已添加全局CSRF豁免配置")
    else:
        print("  - 警告：未找到CSRFProtect初始化代码，无法添加豁免配置")
    
    print("CSRF豁免版本兼容问题修复完成！")

def main():
    """主函数，执行所有修复操作"""
    print(f"===== 开始执行修复脚本 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} =====")
    
    # 执行修复操作
    fix_csrf_exempt_compatibility()
    
    print(f"===== 修复脚本执行完成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} =====")

if __name__ == "__main__":
    main() 