from src import create_app
from src.models import db, Activity
from src.routes.admin import handle_poster_upload
import os
from io import BytesIO
from werkzeug.datastructures import FileStorage
from PIL import Image

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
        activity = db.get_or_404(Activity, 2)
        print(f"活动ID: {activity.id}")
        print(f"活动标题: {activity.title}")
        print(f"当前海报: {activity.poster_image}")
        
        # 创建测试图片
        test_file = create_test_image()
        
        # 测试handle_poster_upload函数
        print("\n测试handle_poster_upload函数:")
        print(f"传递整数ID: {activity.id}")
        poster_filename = handle_poster_upload(test_file, activity.id)
        print(f"返回的文件名: {poster_filename}")
        
        # 更新活动海报
        if poster_filename:
            old_poster = activity.poster_image
            print(f"旧海报: {old_poster}")
            
            activity.poster_image = poster_filename
            db.session.commit()
            
            print(f"更新后的海报: {activity.poster_image}")
            print("海报更新成功!")
        else:
            print("海报上传失败!")
            
    except Exception as e:
        print(f"错误: {e}") 