import os
import sys
import shutil
from datetime import datetime

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 导入必要的模块
from src import create_app
from src.models import db

def fix_education_route():
    """修复教育资源路由问题"""
    print("开始修复教育资源路由问题...")
    
    # 1. 修复路由路径不匹配问题
    education_py_path = os.path.join(current_dir, 'src', 'routes', 'education.py')
    
    with open(education_py_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 将 '/resource/free-fall' 修改为 '/free-fall'
    if "@education_bp.route('/resource/free-fall')" in content:
        content = content.replace(
            "@education_bp.route('/resource/free-fall')",
            "@education_bp.route('/free-fall')"
        )
        print("  - 已修改自由落体路由路径为 '/free-fall'")
    else:
        print("  - 自由落体路由路径无需修改")
    
    # 保存修改后的文件
    with open(education_py_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("教育资源路由问题修复完成！")

def fix_poster_files():
    """修复海报文件缺失问题"""
    print("开始修复海报文件缺失问题...")
    
    # 1. 确保海报目录存在
    static_dir = os.path.join(current_dir, 'src', 'static')
    uploads_dir = os.path.join(static_dir, 'uploads')
    posters_dir = os.path.join(uploads_dir, 'posters')
    
    if not os.path.exists(uploads_dir):
        os.makedirs(uploads_dir)
        print(f"  - 创建了上传目录: {uploads_dir}")
    
    if not os.path.exists(posters_dir):
        os.makedirs(posters_dir)
        print(f"  - 创建了海报目录: {posters_dir}")
    
    # 2. 复制备用风景图到正确位置
    img_dir = os.path.join(static_dir, 'img')
    landscape_src = os.path.join(img_dir, 'landscape.jpg')
    landscape_dst = os.path.join(posters_dir, 'landscape.jpg')
    
    if os.path.exists(landscape_src):
        shutil.copy(landscape_src, landscape_dst)
        print(f"  - 已复制备用风景图到海报目录: {landscape_dst}")
    else:
        # 如果源文件不存在，创建一个空文件作为占位符
        with open(landscape_dst, 'w') as f:
            f.write('')
        print(f"  - 源风景图不存在，已创建空占位文件: {landscape_dst}")
    
    print("海报文件问题修复完成！")

def main():
    """主函数，执行所有修复操作"""
    print(f"===== 开始执行修复脚本 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} =====")
    
    # 执行修复操作
    fix_education_route()
    fix_poster_files()
    
    print(f"===== 修复脚本执行完成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} =====")

if __name__ == "__main__":
    main() 