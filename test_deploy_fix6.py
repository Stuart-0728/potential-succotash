import os
import sys
import re
from datetime import datetime

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 导入必要的模块
from src import create_app

def fix_education_csrf_issues():
    """修复教育资源页面中的CSRF令牌问题"""
    print("开始修复教育资源页面CSRF令牌问题...")
    
    # 1. 修复free_fall.html中的CSRF令牌使用
    free_fall_html_path = os.path.join(current_dir, 'src', 'templates', 'education', 'free_fall.html')
    
    with open(free_fall_html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否使用了csrf_token作为字符串而不是函数
    if '<meta name="csrf-token" content="{{ csrf_token }}">' in content:
        # 备份原始文件
        backup_path = f"{free_fall_html_path}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  - 已备份原始文件到: {backup_path}")
        
        # 将csrf_token修改为csrf_token()函数调用
        modified_content = content.replace(
            '<meta name="csrf-token" content="{{ csrf_token }}">',
            '<meta name="csrf-token" content="{{ csrf_token() }}">'
        )
        
        # 保存修改后的文件
        with open(free_fall_html_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)
            
        print("  - 已将csrf_token修改为csrf_token()函数调用")
    else:
        print("  - 未找到需要修改的CSRF令牌模式或已经正确使用了csrf_token()函数调用")
    
    # 2. 修复gemini_api函数，添加CSRF豁免
    education_py_path = os.path.join(current_dir, 'src', 'routes', 'education.py')
    
    with open(education_py_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否已经导入了csrf_exempt
    if 'from flask_wtf.csrf import CSRFProtect, generate_csrf' in content and 'csrf_exempt' not in content:
        # 备份原始文件
        backup_path = f"{education_py_path}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  - 已备份原始文件到: {backup_path}")
        
        # 修改导入语句，添加csrf_exempt
        modified_content = content.replace(
            'from flask_wtf.csrf import CSRFProtect, generate_csrf',
            'from flask_wtf.csrf import CSRFProtect, generate_csrf, csrf_exempt'
        )
        
        # 添加csrf_exempt装饰器到gemini_api函数
        modified_content = modified_content.replace(
            '@education_bp.route(\'/api/gemini\', methods=[\'POST\'])',
            '@education_bp.route(\'/api/gemini\', methods=[\'POST\'])\n@csrf_exempt'
        )
        
        # 保存修改后的文件
        with open(education_py_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)
            
        print("  - 已将gemini_api函数标记为CSRF豁免")
    else:
        print("  - 已经导入了csrf_exempt或未找到需要修改的导入语句")
    
    print("教育资源页面CSRF令牌问题修复完成！")

def main():
    """主函数，执行所有修复操作"""
    print(f"===== 开始执行修复脚本 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} =====")
    
    # 执行修复操作
    fix_education_csrf_issues()
    
    print(f"===== 修复脚本执行完成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} =====")

if __name__ == "__main__":
    main() 