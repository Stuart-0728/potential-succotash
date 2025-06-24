from src import create_app
from src.models import db, Activity, Tag
from src.routes.admin import handle_poster_upload
import os
from io import BytesIO
from werkzeug.datastructures import FileStorage
from PIL import Image
from datetime import datetime, timedelta
import pytz

app = create_app()

# 创建一个测试图片
def create_test_image():
    img = Image.new('RGB', (100, 100), color='red')
    img_io = BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    return FileStorage(
        stream=img_io,
        filename='test_image.png',
        content_type='image/png'
    )

with app.app_context():
    try:
        # 获取活动
        activity_id = 2
        activity = db.get_or_404(Activity, activity_id)
        print(f"活动ID: {activity.id}")
        print(f"活动标题: {activity.title}")
        print(f"当前海报: {activity.poster_image}")
        print(f"当前标签: {[tag.name for tag in activity.tags]}")
        
        # 创建测试图片
        test_file = create_test_image()
        
        # 测试handle_poster_upload函数
        print("\n测试handle_poster_upload函数:")
        print(f"传递整数ID: {activity.id}")
        poster_filename = handle_poster_upload(test_file, activity.id)
        print(f"返回的文件名: {poster_filename}")
        
        # 修改活动信息
        print("\n模拟编辑活动:")
        old_poster = activity.poster_image
        activity.title = "测试活动标题更新"
        activity.description = "这是一个测试描述更新"
        activity.poster_image = poster_filename
        
        # 修改标签
        print("清空标签并添加新标签")
        activity.tags = []
        
        # 获取一个标签
        tag = db.session.execute(db.select(Tag).limit(1)).scalar_one_or_none()
        if tag:
            activity.tags.append(tag)
            print(f"添加标签: {tag.name}")
        
        # 更新时间
        beijing_tz = pytz.timezone('Asia/Shanghai')
        now = datetime.now(beijing_tz)
        activity.start_time = now + timedelta(days=1)
        activity.end_time = now + timedelta(days=2)
        activity.registration_deadline = now + timedelta(hours=12)
        activity.updated_at = datetime.now(pytz.utc)
        
        # 提交更改
        print("\n提交更改到数据库")
        db.session.commit()
        print("更改已提交")
        
        # 验证更改
        updated_activity = db.get_or_404(Activity, activity_id)
        print("\n验证更改:")
        print(f"活动标题: {updated_activity.title}")
        print(f"活动描述: {updated_activity.description[:30]}...")
        print(f"海报: {updated_activity.poster_image}")
        print(f"标签: {[tag.name for tag in updated_activity.tags]}")
        print(f"开始时间: {updated_activity.start_time}")
        print(f"结束时间: {updated_activity.end_time}")
        print(f"报名截止时间: {updated_activity.registration_deadline}")
        
        print("\n测试完成，所有操作成功!")
            
    except Exception as e:
        print(f"错误: {e}") 