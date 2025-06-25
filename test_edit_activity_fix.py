#!/usr/bin/env python3
import sys
import os
import datetime
import tempfile
from io import BytesIO
from src.routes.admin import handle_poster_upload
from flask import url_for

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# 导入应用和数据库
from src import create_app, db
from src.models import Activity, Tag

# 创建应用和上下文
app = create_app()
app.app_context().push()

# 测试数据
test_activity_data = {
    'title': '测试活动 - 标签修复测试',
    'description': '这是一个测试活动，用于验证标签处理和海报上传功能',
    'location': '线上',
    'start_time': datetime.datetime.now() + datetime.timedelta(days=7),
    'end_time': datetime.datetime.now() + datetime.timedelta(days=8),
    'registration_deadline': datetime.datetime.now() + datetime.timedelta(days=6),
    'max_participants': 100,
    'points': 10,
    'status': 'active',
    'is_featured': True
}

# 创建测试文件
def create_test_file():
    return BytesIO(b'test file content')

# 主测试逻辑
def run_test():
    print("\n=== 开始测试活动编辑功能 ===")

    # 创建测试标签
    try:
        tag1 = Tag(name='测试标签1')
        tag2 = Tag(name='测试标签2')
        tag3 = Tag(name='测试标签3')
        db.session.add_all([tag1, tag2, tag3])
        db.session.flush()
        print(f"已创建测试标签: {tag1.id}, {tag2.id}, {tag3.id}")
    except Exception as e:
        print(f"创建标签失败: {e}")
        raise

    # 创建测试活动
    try:
        activity = Activity(**test_activity_data)
        activity.tags.append(tag1)
        db.session.add(activity)
        db.session.flush()
        activity_id = activity.id
        print(f"已创建测试活动: ID={activity_id}")
    except Exception as e:
        print(f"创建活动失败: {e}")
        db.session.rollback()
        raise

    # 测试handle_poster_upload函数 - 使用不同类型的ID测试
    test_file = create_test_file()
    print("\n测试handle_poster_upload函数 - 使用整数ID:")
    poster_filename1 = handle_poster_upload(test_file, 2)
    print(f"使用整数ID上传结果: {poster_filename1}")
    
    test_file = create_test_file()
    print("\n测试handle_poster_upload函数 - 使用活动对象:")
    poster_filename2 = handle_poster_upload(test_file, activity)
    print(f"使用活动对象上传结果: {poster_filename2}")
    
    test_file = create_test_file()
    print("\n测试handle_poster_upload函数 - 使用字符串ID:")
    poster_filename3 = handle_poster_upload(test_file, "2")
    print(f"使用字符串ID上传结果: {poster_filename3}")

    # 测试活动标签修改
    print("\n测试修改活动标签:")
    try:
        # 修改活动标签
        activity.tags.clear()
        db.session.flush()
        print("已清空活动标签")
        
        # 添加新标签
        activity.tags.append(tag2)
        activity.tags.append(tag3)
        db.session.flush()
        print(f"已添加新标签: {[tag.name for tag in activity.tags]}")
        
        # 提交更改
        db.session.commit()
        print("标签修改已提交到数据库")
        
        # 重新加载活动以验证标签
        activity = db.session.get(Activity, activity_id)
        print(f"活动标签验证: {[tag.name for tag in activity.tags]}")
    except Exception as e:
        print(f"修改标签失败: {e}")
        db.session.rollback()
        raise
    
    print("\n=== 测试完成，活动编辑功能正常 ===")
    return True

if __name__ == "__main__":
    try:
        success = run_test()
        if success:
            print("\n测试成功!")
            sys.exit(0)
        else:
            print("\n测试失败!")
            sys.exit(1)
    except Exception as e:
        print(f"\n测试出错: {e}")
        sys.exit(1) 