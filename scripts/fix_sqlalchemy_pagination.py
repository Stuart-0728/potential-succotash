#!/usr/bin/env python
"""
SQLAlchemy分页修复脚本

在SQLAlchemy 2.0中，分页API发生了变化。此脚本将所有使用旧分页API的代码替换为使用新的兼容性函数。
"""

import os
import re
import sys

def update_file(filepath):
    """
    更新单个文件中的分页代码
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否需要添加导入语句
    if 'get_compatible_paginate' not in content and 'db.paginate' in content:
        # 在其他导入语句后面添加导入语句
        import_pattern = r'(from\s+[\w\.]+\s+import\s+[\w\s,]+\n)'
        last_import = re.findall(import_pattern, content)
        if last_import:
            replacement = last_import[-1] + 'from src.utils import get_compatible_paginate\n'
            content = content.replace(last_import[-1], replacement)
        else:
            # 如果没有找到导入语句，在文件开头添加
            content = 'from src.utils import get_compatible_paginate\n\n' + content
    
    # 替换分页代码
    content = re.sub(
        r'db\.paginate\(([^,]+),\s*page=([^,]+),\s*per_page=([^,\)]+)(?:,\s*[^,\)]+)*\)',
        r'get_compatible_paginate(db, \1, page=\2, per_page=\3, error_out=False)',
        content
    )
    
    # 写回文件
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"已更新: {filepath}")

def main():
    """
    主函数 - 处理整个项目的Python文件
    """
    # 获取项目根目录
    if len(sys.argv) > 1:
        root_dir = sys.argv[1]
    else:
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 源代码目录
    src_dir = os.path.join(root_dir, 'src')
    
    # 检查utils目录是否存在get_compatible_paginate函数
    utils_init_path = os.path.join(src_dir, 'utils', '__init__.py')
    if not os.path.exists(utils_init_path):
        print(f"错误: 未找到文件 {utils_init_path}")
        return
    
    with open(utils_init_path, 'r', encoding='utf-8') as f:
        utils_content = f.read()
    
    if 'get_compatible_paginate' not in utils_content:
        print("错误: 在utils/__init__.py中未找到get_compatible_paginate函数")
        return
    
    # 遍历所有Python文件
    for root, dirs, files in os.walk(src_dir):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 检查文件是否包含db.paginate
                if 'db.paginate' in content:
                    update_file(filepath)

if __name__ == '__main__':
    main() 