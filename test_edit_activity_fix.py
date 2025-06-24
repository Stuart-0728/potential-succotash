from src import create_app
from src.models import db, Activity
from src.routes.admin import handle_poster_upload
import os
from io import BytesIO
from werkzeug.datastructures import FileStorage
from PIL import Image
import logging

# 设置日志记录
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
        logger.info(f"活动ID: {activity.id}")
        logger.info(f"活动标题: {activity.title}")
        logger.info(f"当前海报: {activity.poster_image}")
        
        # 创建测试图片
        test_file = create_test_image()
        
        # 测试handle_poster_upload函数 - 使用不同类型的ID测试
        logger.info("\n测试1: 传递整数ID")
        poster_filename1 = handle_poster_upload(test_file, 2)
        logger.info(f"返回的文件名: {poster_filename1}")
        
        logger.info("\n测试2: 传递活动对象")
        poster_filename2 = handle_poster_upload(test_file, activity)
        logger.info(f"返回的文件名: {poster_filename2}")
        
        logger.info("\n测试3: 传递字符串ID")
        poster_filename3 = handle_poster_upload(test_file, "2")
        logger.info(f"返回的文件名: {poster_filename3}")
        
        # 更新活动海报
        if poster_filename1:
            old_poster = activity.poster_image
            logger.info(f"旧海报: {old_poster}")
            
            activity.poster_image = poster_filename1
            db.session.commit()
            
            logger.info(f"更新后的海报: {activity.poster_image}")
            logger.info("海报更新成功!")
        else:
            logger.error("海报上传失败!")
            
    except Exception as e:
        logger.error(f"错误: {e}", exc_info=True) 