import os
import sys
import re
from datetime import datetime

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 导入必要的模块
from src import create_app
from src.models import db

def fix_csrf_token_issue():
    """修复CSRF令牌问题"""
    print("开始修复CSRF令牌问题...")
    
    # 检查base.html中的CSRF令牌使用方式
    base_html_path = os.path.join(current_dir, 'src', 'templates', 'base.html')
    
    with open(base_html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否使用了csrf_token()函数调用
    if 'content="{{ csrf_token() }}"' in content:
        print("  - base.html中使用了csrf_token()函数调用，这是正确的")
    else:
        print("  - 警告：base.html中可能没有正确使用csrf_token()函数调用")
        # 如果需要修复，可以在这里添加修复代码
    
    print("CSRF令牌问题检查完成！")

def fix_activity_edit_tags():
    """修复活动编辑中的标签处理问题"""
    print("开始修复活动编辑中的标签处理问题...")
    
    admin_py_path = os.path.join(current_dir, 'src', 'routes', 'admin.py')
    
    with open(admin_py_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找edit_activity函数中的form.populate_obj(activity)调用
    if "form.populate_obj(activity)" in content:
        # 备份原始文件
        backup_path = f"{admin_py_path}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  - 已备份原始文件到: {backup_path}")
        
        # 替换form.populate_obj(activity)为手动字段赋值
        # 使用正则表达式查找populate_obj语句所在的代码块
        pattern = r"(# 使用form填充对象\s+)(form\.populate_obj\(activity\))"
        replacement = r"""\1# 手动填充对象字段，避免标签处理错误
                activity.title = form.title.data
                activity.description = form.description.data
                activity.location = form.location.data
                activity.max_participants = form.max_participants.data
                activity.points = form.points.data
                activity.status = form.status.data
                activity.is_featured = form.is_featured.data
                activity.activity_type = form.activity_type.data if hasattr(form, 'activity_type') else None
                # 不处理tags字段，它会在后面单独处理"""
        
        modified_content = re.sub(pattern, replacement, content)
        
        # 保存修改后的文件
        with open(admin_py_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)
        
        print("  - 已替换form.populate_obj(activity)为手动字段赋值")
    else:
        print("  - 未找到form.populate_obj(activity)调用，可能已经修复")
    
    print("活动编辑中的标签处理问题修复完成！")

def main():
    """主函数，执行所有修复操作"""
    print(f"===== 开始执行修复脚本 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} =====")
    
    # 执行修复操作
    fix_csrf_token_issue()
    fix_activity_edit_tags()
    
    print(f"===== 修复脚本执行完成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} =====")

if __name__ == "__main__":
    main() 