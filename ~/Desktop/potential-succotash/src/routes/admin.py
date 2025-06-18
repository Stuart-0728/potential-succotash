from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file, current_app
from flask_login import login_required, current_user
from src.models import User, Activity, Registration, StudentInfo, db, Tag, ActivityReview, ActivityCheckin, Role, PointsHistory
from src.routes.utils import admin_required, log_action
from datetime import datetime, timedelta
import pandas as pd
import io
import logging
import json
from sqlalchemy import func, desc, and_
from src.forms import ActivityForm, SearchForm
import os
import shutil
from werkzeug.utils import secure_filename
import qrcode
from io import BytesIO
from src import cache
import hashlib

admin_bp = Blueprint('admin', __name__)
logger = logging.getLogger(__name__)

@admin_bp.route('/api/qrcode/checkin/<int:id>')
@admin_required
def generate_checkin_qrcode(id):
    try:
        # 检查活动是否存在
        activity = Activity.query.get_or_404(id)
        
        # 生成唯一签到密钥，确保时效性和安全性
        checkin_key = hashlib.sha256(f"{activity.id}:{datetime.now().timestamp()}:{current_app.config['SECRET_KEY']}".encode()).hexdigest()[:16]
        
        # 优先使用数据库存储，如果数据库操作失败则使用缓存
        try:
            activity.checkin_key = checkin_key
            activity.checkin_key_expires = datetime.now() + timedelta(hours=24)  # 24小时有效期
            db.session.commit()
        except Exception as e:
            logger.error(f"无法存储签到密钥到数据库: {e}")
            # 使用缓存作为备选方案
            cache_key = f"checkin_key_{activity.id}"
            cache.set(cache_key, checkin_key, timeout=86400)  # 24小时 = 86400秒
        
        # 生成带签到URL的二维码，使用完整域名
        base_url = request.host_url.rstrip('/')
        checkin_url = f"{base_url}/checkin/scan/{activity.id}/{checkin_key}"
        
        # 创建QR码实例 - 优化参数
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,  # 提高错误纠正级别
            box_size=10,
            border=4,
        )
        
        # 添加URL数据
        qr.add_data(checkin_url)
        qr.make(fit=True)
        
        # 创建图像
        qr_image = qr.make_image(fill_color="black", back_color="white")
        
        # 保存到内存
        img_buffer = BytesIO()
        qr_image.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        return send_file(
            img_buffer,
            mimetype='image/png',
            as_attachment=False,
            download_name='checkin_qrcode.png'
        )
        
    except Exception as e:
        logger.error(f"生成签到二维码时出错: {e}")
        return jsonify({'error': '生成二维码失败'}), 500

# 添加二维码签到跳转路由
@admin_bp.route('/checkin/modal/<int:id>')
@admin_required
def checkin_modal(id):
    activity = Activity.query.get_or_404(id)
    return render_template('admin/checkin_modal.html', activity=activity) 