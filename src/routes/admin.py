import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import logging
from datetime import datetime, timedelta
import hashlib
import json
import re
import io
from io import BytesIO  # 添加BytesIO导入
import csv
import qrcode
from PIL import Image
import base64
import pandas as pd  # 添加pandas导入
import tempfile  # 添加tempfile导入
import zipfile  # 添加zipfile导入
import pytz
from flask import (
    Blueprint, render_template, redirect, url_for, flash, request, current_app, 
    send_from_directory, send_file, Response, make_response, jsonify
)
from flask_login import current_user, login_required
from sqlalchemy import func, desc, or_, and_, extract, text, case
from sqlalchemy.orm import joinedload
from werkzeug.utils import secure_filename
from src.models import db, User, Role, StudentInfo, Activity, Registration, SystemLog, Tag, Message, Notification, NotificationRead, PointsHistory, ActivityReview, ActivityCheckin, AIChatHistory, AIChatSession, AIUserPreferences, student_tags, activity_tags, Announcement
from src.routes.utils import admin_required, log_action
from src.utils.time_helpers import normalize_datetime_for_db, display_datetime, ensure_timezone_aware, get_beijing_time, get_localized_now, safe_less_than, safe_greater_than
from src.forms import ActivityForm  # 添加ActivityForm导入
from flask_wtf.csrf import generate_csrf, validate_csrf
from src.utils import get_compatible_paginate

# 创建蓝图
admin_bp = Blueprint('admin', __name__)

# 配置日志记录器
logger = logging.getLogger(__name__)

def handle_poster_upload(file_data, activity_id):
    """处理活动海报上传
    
    Args:
        file_data: 文件对象
        activity_id: 活动ID
    
    Returns:
        dict: 包含文件名、二进制数据和MIME类型的字典
    """
    try:
        if not file_data or not hasattr(file_data, 'filename') or not file_data.filename:
            logger.warning("无效的文件上传")
            return None
        
        logger.info(f"开始处理海报上传: 文件名={file_data.filename}, 活动ID={activity_id}")
        
        # 确保文件名安全
        filename = secure_filename(file_data.filename)
        
        # 获取MIME类型
        mime_type = file_data.mimetype
        logger.info(f"文件MIME类型: {mime_type}")
        
        # 生成唯一文件名 - 确保活动ID不为None
        _, file_extension = os.path.splitext(filename)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        
        # 确保 activity_id 是有效的字符串
        if activity_id is None:
            unique_filename = f"activity_temp_{timestamp}{file_extension}"
            logger.info(f"活动ID为空，使用临时ID: {unique_filename}")
        else:
            # 先转换成字符串，处理整数ID情况
            if isinstance(activity_id, int):
                str_activity_id = str(activity_id)
                logger.info(f"活动ID是整数，直接转换为字符串: {str_activity_id}")
            else:
                # 处理活动ID - 如果是对象，获取id属性；如果是基本类型，直接使用
                try:
                    # 尝试访问id属性，适用于ORM对象
                    if hasattr(activity_id, 'id'):
                        str_activity_id = str(activity_id.id)
                        logger.info(f"从对象中提取活动ID: {str_activity_id}")
                    else:
                        # 如果不是对象或没有id属性，直接使用
                        str_activity_id = str(activity_id)
                        logger.info(f"直接使用活动ID: {str_activity_id}")
                except Exception as e:
                    # 如果出错，直接尝试转换为字符串
                    str_activity_id = str(activity_id)
                    logger.warning(f"处理活动ID时出错，使用直接转换: {str_activity_id}, 错误: {e}")
            
            unique_filename = f"activity_{str_activity_id}_{timestamp}{file_extension}"
        
        logger.info(f"生成的唯一文件名: {unique_filename}")
        
        # 保存到文件系统 (同时保留这部分，确保向后兼容)
        try:
            # 确保上传目录存在
            upload_dir = current_app.config['UPLOAD_FOLDER']
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir, exist_ok=True)
                logger.info(f"创建上传目录: {upload_dir}")
            
            # 保存文件
            file_path = os.path.join(upload_dir, unique_filename)
            file_data.save(file_path)
            logger.info(f"海报文件已保存到: {file_path}")
            
            # 设置文件权限为可读
            try:
                os.chmod(file_path, 0o644)
                logger.info(f"设置文件权限为644: {file_path}")
            except Exception as e:
                logger.warning(f"无法设置文件权限: {e}")
        except Exception as e:
            logger.warning(f"保存文件到文件系统失败: {e}")
        
        # 读取二进制数据 (先保存文件再读取是为了确保文件指针位置正确)
        file_data.seek(0)
        binary_data = file_data.read()
        logger.info(f"已读取二进制数据，大小: {len(binary_data)} 字节")
        
        # 返回文件信息 (包含文件名、二进制数据和MIME类型)
        logger.info(f"活动海报已处理: {unique_filename}")
        return {
            'filename': unique_filename,
            'data': binary_data,
            'mimetype': mime_type
        }
        
    except Exception as e:
        logger.error(f"海报上传失败: {str(e)}", exc_info=True)
        return None

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    # 导入display_datetime函数供所有模板使用
    from src.utils.time_helpers import display_datetime
    try:
        # 获取基本统计数据
        total_students_stmt = db.select(func.count()).select_from(StudentInfo)
        total_students = db.session.execute(total_students_stmt).scalar()
        
        total_activities_stmt = db.select(func.count()).select_from(Activity)
        total_activities = db.session.execute(total_activities_stmt).scalar()
        
        active_activities_stmt = db.select(func.count()).select_from(Activity).filter_by(status='active')
        active_activities = db.session.execute(active_activities_stmt).scalar()
        
        # 获取最近活动
        recent_activities_stmt = db.select(Activity).order_by(Activity.created_at.desc()).limit(5)
        recent_activities = db.session.execute(recent_activities_stmt).scalars().all()
        
        # 获取最近注册的学生 - 修复查询，使用Role关联而不是role_id
        recent_students_stmt = db.select(User).join(Role).filter(Role.name == 'Student').join(
            StudentInfo, User.id == StudentInfo.user_id
        ).order_by(User.created_at.desc()).limit(5)
        recent_students = db.session.execute(recent_students_stmt).scalars().all()
        
        # 获取报名统计
        total_registrations_stmt = db.select(func.count()).select_from(Registration)
        total_registrations = db.session.execute(total_registrations_stmt).scalar()
        
        return render_template('admin/dashboard.html',
                              total_students=total_students,
                              total_activities=total_activities,
                              active_activities=active_activities,
                              recent_activities=recent_activities,
                              recent_students=recent_students,
                              total_registrations=total_registrations,
                              display_datetime=display_datetime,
                              Registration=Registration)
    except Exception as e:
        logger.error(f"Error in admin dashboard: {e}")
        flash('加载管理面板时出错', 'danger')
        return render_template('admin/dashboard.html')

@admin_bp.route('/activities')
@admin_bp.route('/activities/<status>')
@admin_required
def activities(status='all'):
    try:
        from src.utils import get_compatible_paginate
        
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '')
        
        # 基本查询
        query = db.select(Activity)
        
        # 搜索功能
        if search:
            query = query.filter(
                db.or_(
                    Activity.title.ilike(f'%{search}%'),
                    Activity.description.ilike(f'%{search}%')
                )
            )
        
        # 状态筛选
        if status == 'upcoming':
            now = get_localized_now()
            query = query.filter(
                Activity.status == 'active',
                Activity.start_time > now
            )
        elif status == 'active':
            query = query.filter(Activity.status == 'active')
        elif status == 'completed':
            query = query.filter(Activity.status == 'completed')
        elif status == 'cancelled':
            query = query.filter(Activity.status == 'cancelled')
        
        # 排序
        query = query.order_by(Activity.created_at.desc())
        
        # 使用兼容性分页查询
        activities = get_compatible_paginate(db, query, page=page, per_page=10, error_out=False)
        
        # 优化：使用子查询一次性获取所有活动的报名人数
        activity_ids = [activity.id for activity in activities.items]
        if activity_ids:
            reg_counts_stmt = db.select(
                Registration.activity_id,
                func.count(Registration.id).label('count')
            ).filter(
                Registration.activity_id.in_(activity_ids),
                or_(
                    Registration.status == 'registered',
                    Registration.status == 'attended'
                )
            ).group_by(Registration.activity_id)
            
            reg_counts_result = db.session.execute(reg_counts_stmt).all()
            registration_counts = {activity_id: count for activity_id, count in reg_counts_result}
        else:
            registration_counts = {}
        
        # 导入display_datetime函数供模板使用
        from src.utils.time_helpers import display_datetime
        
        return render_template('admin/activities.html', 
                              activities=activities, 
                              current_status=status,
                              registration_counts=registration_counts,
                              display_datetime=display_datetime)
    except Exception as e:
        logger.error(f"Error in activities page: {e}")
        flash('加载活动列表时出错', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/activity/create', methods=['GET', 'POST'])
@admin_required
def create_activity():
    """创建活动"""
    form = ActivityForm()
    
    # 加载所有标签并设置选项
    tags_stmt = db.select(Tag).order_by(Tag.name)
    tags = db.session.execute(tags_stmt).scalars().all()
    choices = [(tag.id, tag.name) for tag in tags]
    form.tags.choices = choices
    
    if form.validate_on_submit():
        try:
            # 获取表单数据
            title = form.title.data
            description = form.description.data
            location = form.location.data
            start_time = form.start_time.data
            end_time = form.end_time.data
            registration_deadline = form.registration_deadline.data
            max_participants = form.max_participants.data
            points = form.points.data
            status = form.status.data
            is_featured = form.is_featured.data
            
            # 改进的时区处理逻辑
            # 先检查时间对象是否为None
            if start_time:
                # 检查是否已有时区信息，避免重复添加
                if start_time.tzinfo is None:
                    start_time = ensure_timezone_aware(start_time)
                    logger.info(f"为start_time添加了北京时区: {start_time}")
                else:
                    # 如果已有时区信息，只需确保是UTC时区
                    start_time = start_time.astimezone(pytz.utc)
            
            if end_time:
                # 检查是否已有时区信息，避免重复添加
                if end_time.tzinfo is None:
                    end_time = ensure_timezone_aware(end_time)
                    logger.info(f"为end_time添加了北京时区: {end_time}")
                else:
                    # 如果已有时区信息，只需确保是UTC时区
                    end_time = end_time.astimezone(pytz.utc)
            
            if registration_deadline:
                # 检查是否已有时区信息，避免重复添加
                if registration_deadline.tzinfo is None:
                    registration_deadline = ensure_timezone_aware(registration_deadline)
                    logger.info(f"为registration_deadline添加了北京时区: {registration_deadline}")
                else:
                    # 如果已有时区信息，只需确保是UTC时区
                    registration_deadline = registration_deadline.astimezone(pytz.utc)
            
            # 创建活动
            activity = Activity(
                title=title,
                description=description,
                location=location,
                start_time=start_time,
                end_time=end_time,
                registration_deadline=registration_deadline,
                max_participants=max_participants,
                points=points,
                status=status,
                is_featured=is_featured,
                created_by=current_user.id
            )
            
            # 处理标签
            selected_tag_ids = request.form.getlist('tags')
            if selected_tag_ids:
                # 根据ID直接查询标签对象
                valid_tag_ids = []
                for tag_id_str in selected_tag_ids:
                    try:
                        if tag_id_str and str(tag_id_str).strip().isdigit():
                            valid_tag_ids.append(int(tag_id_str))
                    except Exception as e:
                        logger.warning(f"处理标签ID时出错: {e}, tag_id={tag_id_str}")
                
                logger.info(f"活动标签处理 - 有效标签ID: {valid_tag_ids}")
                
                # 批量获取标签
                if valid_tag_ids:
                    tags_stmt = db.select(Tag).filter(Tag.id.in_(valid_tag_ids))
                    selected_tags = db.session.execute(tags_stmt).scalars().all()
                    logger.info(f"活动标签处理 - 找到{len(selected_tags)}个标签")
                    
                    # 添加标签关联
                    for tag in selected_tags:
                        activity.tags.append(tag)
                        logger.info(f"活动标签处理 - 添加标签: [{tag.id}]{tag.name}")
            
            # 处理海报图片上传
            if form.poster.data and hasattr(form.poster.data, 'filename') and form.poster.data.filename:
                try:
                    # 记录调试信息
                    logger.info(f"准备上传海报，活动ID={activity.id}, 文件名={form.poster.data.filename}")
                    
                    # 使用活动的实际ID上传图片
                    poster_info = handle_poster_upload(form.poster.data, activity.id)
                    if poster_info:
                        # 记录旧海报文件名，以便稍后删除
                        old_poster = activity.poster_image
                        
                        # 更新海报信息
                        activity.poster_image = poster_info['filename']
                        activity.poster_data = poster_info['data']
                        activity.poster_mimetype = poster_info['mimetype']
                        logger.info(f"活动海报信息已更新: {poster_info['filename']}")
                        
                        # 尝试删除旧海报文件（如果存在且不是默认banner）
                        if old_poster and 'banner' not in old_poster:
                            try:
                                old_poster_path = os.path.join(current_app.static_folder or 'src/static', 'uploads', 'posters', old_poster)
                                if os.path.exists(old_poster_path):
                                    os.remove(old_poster_path)
                                    logger.info(f"已删除旧海报文件: {old_poster_path}")
                            except Exception as e:
                                logger.warning(f"删除旧海报文件时出错: {e}")
                    else:
                        logger.error("上传海报失败，未获得有效的文件信息")
                        flash('上传海报失败，请重试', 'warning')
                except Exception as e:
                    logger.error(f"上传海报时出错: {e}", exc_info=True)
                    flash('上传海报时出错，但活动信息已保存', 'warning')
            
            # 保存到数据库
            db.session.add(activity)
            db.session.commit()
            
            # 记录操作
            log_action(
                user_id=current_user.id,
                action="create_activity",
                details=f"创建了活动 {activity.id}: {activity.title}"
            )
            
            flash('活动创建成功', 'success')
            return redirect(url_for('admin.activities'))
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error in create_activity: {str(e)}")
            flash(f'创建活动失败: {str(e)}', 'danger')
    
    # GET请求或表单验证失败
    return render_template('admin/activity_form.html', form=form, activity=None)

@admin_bp.route('/activity/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_activity(id):
    try:
        # 获取活动对象
        activity = db.get_or_404(Activity, id)
        form = ActivityForm(obj=activity)
        
        # 加载所有标签并设置选项
        tags_stmt = db.select(Tag).order_by(Tag.name)
        tags = db.session.execute(tags_stmt).scalars().all()
        form.tags.choices = [(tag.id, tag.name) for tag in tags]
        
        # 设置当前已有的标签
        if request.method == 'GET':
            try:
                form.tags.data = [tag.id for tag in activity.tags]
                logger.info(f"已设置活动 {id} 的当前标签: {form.tags.data}")
            except Exception as e:
                logger.error(f"设置当前标签时出错: {e}")
                form.tags.data = []
        
        if form.validate_on_submit():
            try:
                # 导入pytz用于时区处理
                beijing_tz = pytz.timezone('Asia/Shanghai')
                
                # 更新活动信息，但先保存标签引用
                selected_tag_ids = request.form.getlist('tags')
                logger.info(f"选中的标签IDs: {selected_tag_ids}")
                
                # 使用form填充对象，但先处理poster字段
                # 防止文件字段被意外设置为字符串
                poster_data = form.poster.data
                form.poster.data = None
                
                # 保存当前签到设置和创建者ID，因为表单中没有这些字段
                checkin_enabled = activity.checkin_enabled
                checkin_key = activity.checkin_key
                checkin_key_expires = activity.checkin_key_expires
                created_by_id = activity.created_by  # 保存创建者ID
                
                # 先保存表单中的时间字段，将它们转换为带时区的UTC时间
                start_time = form.start_time.data
                if start_time:
                    # 检查是否已有时区信息，避免重复添加
                    if start_time.tzinfo is None:
                        start_time = beijing_tz.localize(start_time).astimezone(pytz.utc)
                    else:
                        # 如果已有时区信息，只需确保是UTC时区
                        start_time = start_time.astimezone(pytz.utc)
                
                end_time = form.end_time.data
                if end_time:
                    # 检查是否已有时区信息，避免重复添加
                    if end_time.tzinfo is None:
                        end_time = beijing_tz.localize(end_time).astimezone(pytz.utc)
                    else:
                        # 如果已有时区信息，只需确保是UTC时区
                        end_time = end_time.astimezone(pytz.utc)
                
                registration_deadline = form.registration_deadline.data
                if registration_deadline:
                    # 检查是否已有时区信息，避免重复添加
                    if registration_deadline.tzinfo is None:
                        registration_deadline = beijing_tz.localize(registration_deadline).astimezone(pytz.utc)
                    else:
                        # 如果已有时区信息，只需确保是UTC时区
                        registration_deadline = registration_deadline.astimezone(pytz.utc)
                
                # 使用form填充对象
                # 手动填充对象字段，避免标签处理错误
                activity.title = form.title.data
                activity.description = form.description.data
                activity.location = form.location.data
                activity.max_participants = form.max_participants.data
                activity.points = form.points.data
                activity.status = form.status.data
                activity.is_featured = form.is_featured.data
                activity.activity_type = form.activity_type.data if hasattr(form, 'activity_type') else None
                # 不处理tags字段，它会在后面单独处理
                
                # 使用转换后的时间覆盖填充的时间字段
                activity.start_time = start_time
                activity.end_time = end_time
                activity.registration_deadline = registration_deadline
                
                # 恢复保存的值
                activity.checkin_enabled = checkin_enabled
                activity.checkin_key = checkin_key
                activity.checkin_key_expires = checkin_key_expires
                
                # 恢复创建者ID
                activity.created_by = created_by_id
                
                # 恢复poster数据以便后续处理
                form.poster.data = poster_data
                
                # 处理标签 - 使用更直接的方式处理标签关系
                try:
                    # 将选中的标签ID转换为整数
                    new_tag_ids = []
                    for tag_id_str in selected_tag_ids:
                        try:
                            tag_id = int(tag_id_str.strip())
                            new_tag_ids.append(tag_id)
                        except (ValueError, TypeError) as e:
                            logger.warning(f"无效的标签ID: {tag_id_str}, 错误: {e}")
                    
                    logger.info(f"新选中的标签IDs: {new_tag_ids}")
                    
                    # 直接查询所有需要的标签对象
                    if new_tag_ids:
                        # 一次性查询所有标签
                        tags = db.session.execute(
                            db.select(Tag).filter(Tag.id.in_(new_tag_ids))
                        ).scalars().all()
                        
                        # 创建ID到标签对象的映射
                        tag_map = {tag.id: tag for tag in tags}
                        logger.info(f"找到{len(tags)}个标签对象")
                        
                        # 完全重置标签关系
                        # 先获取当前关联的所有标签
                        current_tags = list(activity.tags)
                        
                        # 移除所有当前标签
                        for tag in current_tags:
                            activity.tags.remove(tag)
                        
                        logger.info("已移除所有现有标签")
                        
                        # 添加新标签
                        for tag_id in new_tag_ids:
                            if tag_id in tag_map:
                                activity.tags.append(tag_map[tag_id])
                                logger.info(f"添加标签: {tag_id}")
                            else:
                                logger.warning(f"找不到标签ID: {tag_id}")
                    else:
                        # 如果没有选择标签，则移除所有标签
                        current_tags = list(activity.tags)
                        for tag in current_tags:
                            activity.tags.remove(tag)
                        logger.info("没有选择标签，已移除所有现有标签")
                    
                    logger.info(f"标签处理完成，共添加{len(activity.tags)}个标签")
                
                except Exception as e:
                    logger.error(f"处理标签时出错: {e}", exc_info=True)
                    flash('处理活动标签时出错，其他信息已尝试保存', 'warning')
                
                # 更新积分，确保重点活动有足够积分
                if activity.is_featured and (activity.points is None or activity.points < 20):
                    activity.points = 20
                
                # 处理上传的图片
                if form.poster.data and hasattr(form.poster.data, 'filename') and form.poster.data.filename:
                    try:
                        logger.info(f"编辑活动: 准备上传海报，活动ID={activity.id}, 文件名={form.poster.data.filename}")
                        
                        # 使用handle_poster_upload函数处理文件上传，确保传递活动ID（整数）而不是整个活动对象
                        poster_info = handle_poster_upload(form.poster.data, activity.id)
                        
                        if poster_info:
                            # 记录旧海报文件名，以便稍后删除
                            old_poster = activity.poster_image
                            
                            # 更新海报信息
                            activity.poster_image = poster_info['filename']
                            activity.poster_data = poster_info['data']
                            activity.poster_mimetype = poster_info['mimetype']
                            logger.info(f"编辑活动: 海报信息已更新: {poster_info['filename']}")
                            
                            # 尝试删除旧海报文件（如果存在且不是默认banner）
                            if old_poster and 'banner' not in old_poster:
                                try:
                                    old_poster_path = os.path.join(current_app.static_folder or 'src/static', 'uploads', 'posters', old_poster)
                                    if os.path.exists(old_poster_path):
                                        os.remove(old_poster_path)
                                        logger.info(f"编辑活动: 已删除旧海报文件: {old_poster_path}")
                                except Exception as e:
                                    logger.warning(f"编辑活动: 删除旧海报文件时出错: {e}")
                        else:
                            logger.error("编辑活动: 上传海报失败，未获得有效的文件信息")
                            flash('上传海报时出错，但其他活动信息已保存', 'warning')
                    except Exception as e:
                        logger.error(f"编辑活动: 上传海报时出错: {e}", exc_info=True)
                        flash('上传海报时出错，但其他活动信息已保存', 'warning')
                
                # 记录更新时间，使用UTC时间
                activity.updated_at = datetime.now(pytz.utc)
                
                # 如果状态变为已完成，记录完成时间
                if activity.status == 'completed' and not activity.completed_at:
                    activity.completed_at = datetime.now(pytz.utc)
                
                # 提交前记录详细信息，帮助诊断问题
                logger.info(f"准备提交活动更新 - ID: {activity.id}, 标题: {activity.title}, 海报: {activity.poster_image}")
                logger.info(f"标签数量: {len(activity.tags)}")
                
                try:
                    db.session.commit()
                    logger.info("活动更新成功提交到数据库")
                    
                    # 记录日志
                    log_action('edit_activity', f'编辑活动: {activity.title}')
                    
                    flash('活动更新成功!', 'success')
                    return redirect(url_for('admin.activities'))
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"提交活动更新时出错: {e}", exc_info=True)
                    flash(f'保存活动时出错: {str(e)}', 'danger')
                    return render_template('admin/activity_form.html', form=form, title='编辑活动', activity=activity)
            except Exception as e:
                db.session.rollback()
                logger.error(f"编辑活动时出错: {e}", exc_info=True)
                flash(f'编辑活动时出错: {str(e)}', 'danger')
                return render_template('admin/activity_form.html', form=form, title='编辑活动', activity=activity)
        
        return render_template('admin/activity_form.html', form=form, title='编辑活动', activity=activity)
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in edit_activity: {e}", exc_info=True)
        flash('编辑活动时出错', 'danger')
        return redirect(url_for('admin.activities'))

@admin_bp.route('/students')
@admin_required
def students():
    try:
        from src.utils import get_compatible_paginate
        
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '')
        
        # 使用SQLAlchemy 2.0风格查询
        query = db.select(StudentInfo).join(User, StudentInfo.user_id == User.id)
        
        if search:
            query = query.filter(
                db.or_(
                    StudentInfo.real_name.ilike(f'%{search}%'),
                    StudentInfo.student_id.ilike(f'%{search}%'),
                    StudentInfo.college.ilike(f'%{search}%'),
                    StudentInfo.major.ilike(f'%{search}%'),
                    User.username.ilike(f'%{search}%')
                )
            )
        
        # 使用兼容性分页
        query = query.order_by(StudentInfo.id.desc())
        students = get_compatible_paginate(db, query, page=page, per_page=20, error_out=False)
        
        # 确保所有学生记录都有qq和has_selected_tags字段的值
        for student in students.items:
            if not hasattr(student, 'qq'):
                student.qq = ''
            if not hasattr(student, 'has_selected_tags'):
                student.has_selected_tags = False
        
        return render_template('admin/students.html', students=students, search=search)
    except Exception as e:
        logger.error(f"Error in students: {e}")
        flash('加载学生列表时出错', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/student/<int:id>/delete', methods=['POST'])
@admin_required
def delete_student(id):
    try:
        user = db.get_or_404(User, id)
        if user.role.name != 'Student':
            flash('只能删除学生账号', 'danger')
            return redirect(url_for('admin.students'))

        db.session.delete(user)
        db.session.commit()

        log_action('delete_student', f'删除学生账号: {user.username}')
        flash('学生账号已成功删除', 'success')
        return redirect(url_for('admin.students'))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting student: {e}")
        flash('删除学生账号时出错', 'danger')
        return redirect(url_for('admin.students'))

@admin_bp.route('/student/<int:user_id>')
@admin_required
def student_view(user_id):
    # 导入display_datetime函数
    from src.utils.time_helpers import display_datetime
    
    user = db.get_or_404(User, user_id)
    student = db.session.execute(db.select(StudentInfo).filter_by(user_id=user_id)).scalar_one_or_none()
    if not student:
        flash('未找到该学生的详细信息', 'warning')
        return redirect(url_for('admin.students'))
    
    # 使用SQLAlchemy 2.0风格查询
    points_stmt = db.select(PointsHistory).filter_by(student_id=student.id).order_by(PointsHistory.created_at.desc())
    points_history = db.session.execute(points_stmt).scalars().all()
    
    reg_stmt = db.select(Registration).filter_by(user_id=user.id).options(joinedload(Registration.activity))
    registrations = db.session.execute(reg_stmt).scalars().all()
    
    # 获取学生的标签
    selected_tag_ids = [tag.id for tag in student.tags] if student.tags else []
    
    # 获取所有标签
    tags_stmt = db.select(Tag)
    all_tags = db.session.execute(tags_stmt).scalars().all()
    
    return render_template('admin/student_view.html', student=student, user=user, 
                           points_history=points_history, registrations=registrations,
                           selected_tag_ids=selected_tag_ids, all_tags=all_tags,
                           display_datetime=display_datetime)

@admin_bp.route('/student/<int:id>/update-tags', methods=['POST'])
@admin_required
def update_student_tags(id):
    student = db.get_or_404(StudentInfo, id)
    
    try:
        # 获取提交的标签ID
        tag_ids = request.form.getlist('tags')
        
        # 清除原有标签关联
        student.tags = []
        
        # 添加新的标签关联
        for tag_id in tag_ids:
            tag_stmt = db.select(Tag).filter_by(id=int(tag_id))
            tag = db.session.execute(tag_stmt).scalar_one_or_none()
            if tag:
                student.tags.append(tag)
        
        # 更新学生标签选择状态
        if hasattr(student, 'has_selected_tags'):
            student.has_selected_tags = True if tag_ids else False
        db.session.commit()
        
        flash('学生标签更新成功！', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"更新学生标签时出错: {e}")
        flash('更新学生标签时出错', 'danger')
    
    return redirect(url_for('admin.student_view', user_id=student.user_id))

@admin_bp.route('/student/<int:id>/adjust_points', methods=['POST'])
@admin_required
def adjust_student_points(id):
    try:
        student_info = db.get_or_404(StudentInfo, id)
        points = request.form.get('points', type=int)
        reason = request.form.get('reason', '').strip()
        
        if not points:
            flash('请输入有效的积分值', 'warning')
            return redirect(url_for('admin.student_view', user_id=student_info.user_id))
        
        if not reason:
            flash('请输入积分调整原因', 'warning')
            return redirect(url_for('admin.student_view', user_id=student_info.user_id))
        
        # 更新学生积分
        student_info.points = (student_info.points or 0) + points
        
        # 创建积分历史记录
        points_history = PointsHistory(
            student_id=id,
            points=points,
            reason=f"管理员调整: {reason}",
            activity_id=None
        )
        
        db.session.add(points_history)
        db.session.commit()
        
        log_action('adjust_points', f'调整学生 {student_info.real_name} (ID: {id}) 的积分: {points}分, 原因: {reason}')
        flash(f'积分调整成功，当前积分: {student_info.points}', 'success')
        
        return redirect(url_for('admin.student_view', user_id=student_info.user_id))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in adjust_student_points: {e}")
        flash('调整积分时出错', 'danger')
        return redirect(url_for('admin.student_view', user_id=student_info.user_id))

@admin_bp.route('/statistics')
@admin_required
def statistics():
    try:
        # 获取当前时间
        now = get_localized_now()
        
        # 获取最近7天的日期范围
        end_date = now
        start_date = end_date - timedelta(days=6)
        
        # 确保时间是规范化的
        start_date = normalize_datetime_for_db(start_date)
        end_date = normalize_datetime_for_db(end_date)
        
        # 获取最近7天的活动数据
        daily_activities_stmt = db.select(
            func.date(Activity.created_at).label('date'),
            func.count(Activity.id).label('count')
        ).filter(
            Activity.created_at.between(start_date, end_date)
        ).group_by(
            func.date(Activity.created_at)
        )
        daily_activities = db.session.execute(daily_activities_stmt).all()
        
        # 获取最近7天的注册数据
        daily_registrations_stmt = db.select(
            func.date(Registration.register_time).label('date'),
            func.count(Registration.id).label('count')
        ).filter(
            Registration.register_time.between(start_date, end_date)
        ).group_by(
            func.date(Registration.register_time)
        )
        daily_registrations = db.session.execute(daily_registrations_stmt).all()
        
        # 获取最近7天的用户注册数据
        daily_users_stmt = db.select(
            func.date(User.created_at).label('date'),
            func.count(User.id).label('count')
        ).filter(
            User.created_at.between(start_date, end_date)
        ).group_by(
            func.date(User.created_at)
        )
        daily_users = db.session.execute(daily_users_stmt).all()
        
        # 将查询结果转换为字典格式，方便前端使用
        date_format = '%Y-%m-%d'
        
        # 创建包含所有日期的字典
        date_range = [(start_date + timedelta(days=i)).strftime(date_format) for i in range(7)]
        
        activities_data = {date: 0 for date in date_range}
        for item in daily_activities:
            date_str = item.date.strftime(date_format) if hasattr(item.date, 'strftime') else str(item.date)
            activities_data[date_str] = item.count
            
        registrations_data = {date: 0 for date in date_range}
        for item in daily_registrations:
            date_str = item.date.strftime(date_format) if hasattr(item.date, 'strftime') else str(item.date)
            registrations_data[date_str] = item.count
            
        users_data = {date: 0 for date in date_range}
        for item in daily_users:
            date_str = item.date.strftime(date_format) if hasattr(item.date, 'strftime') else str(item.date)
            users_data[date_str] = item.count
        
        # 准备图表数据
        chart_data = {
            'labels': date_range,
            'activities': [activities_data[date] for date in date_range],
            'registrations': [registrations_data[date] for date in date_range],
            'users': [users_data[date] for date in date_range]
        }
        
        # 获取活动类型分布
        activity_types_stmt = db.select(
            Activity.type,
            func.count(Activity.id).label('count')
        ).group_by(Activity.type)
        activity_types = db.session.execute(activity_types_stmt).all()
        
        # 转换为前端可用的格式
        type_labels = [t.type for t in activity_types]
        type_data = [t.count for t in activity_types]
        
        # 获取标签统计
        try:
            tag_stats_stmt = db.select(
                Tag.name,
                func.count(Activity.id).label('count')
            ).join(
                activity_tags, Tag.id == activity_tags.c.tag_id
            ).join(
                Activity, Activity.id == activity_tags.c.activity_id
            ).group_by(Tag.name).order_by(desc('count')).limit(10)
            
            tag_stats = db.session.execute(tag_stats_stmt).all()
            
            # 转换为前端可用的格式
            tag_labels = [t.name for t in tag_stats]
            tag_data = [t.count for t in tag_stats]
        except Exception as e:
            logger.error(f"获取标签统计失败: {e}")
            tag_labels = []
            tag_data = []
        
        return render_template(
            'admin/statistics.html',
            chart_data=chart_data,
            type_labels=type_labels,
            type_data=type_data,
            tag_labels=tag_labels,
            tag_data=tag_data
        )
    except Exception as e:
        logger.error(f"Error in statistics: {e}")
        flash('加载统计数据时出错', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/api/statistics')
@admin_bp.route('/admin/api/statistics')  # 添加一个包含admin前缀的路由
@admin_required
def api_statistics():
    try:
        # 活动状态统计
        active_count_stmt = db.select(func.count()).select_from(Activity).filter_by(status='active')
        active_count = db.session.execute(active_count_stmt).scalar()
        
        completed_count_stmt = db.select(func.count()).select_from(Activity).filter_by(status='completed')
        completed_count = db.session.execute(completed_count_stmt).scalar()
        
        cancelled_count_stmt = db.select(func.count()).select_from(Activity).filter_by(status='cancelled')
        cancelled_count = db.session.execute(cancelled_count_stmt).scalar()
        
        registration_stats = {
            'labels': ['进行中', '已结束', '已取消'],
            'data': [active_count, completed_count, cancelled_count]
        }
        
        # 学生参与度统计
        student_role_stmt = db.select(Role.id).filter_by(name='Student')
        student_role_id = db.session.execute(student_role_stmt).scalar()
        
        total_students_stmt = db.select(func.count()).select_from(User).filter_by(role_id=student_role_id)
        total_students = db.session.execute(total_students_stmt).scalar()
        
        active_students_stmt = db.select(func.count(Registration.user_id.distinct())).select_from(Registration)
        active_students = db.session.execute(active_students_stmt).scalar()
        
        inactive_students = total_students - active_students if total_students > active_students else 0
        
        participation_stats = {
            'labels': ['已参与活动', '未参与活动'],
            'data': [active_students, inactive_students]
        }
        
        # 月度活动和报名统计
        months = []
        activities_count = []
        registrations_count = []
        
        for i in range(5, -1, -1):
            # 获取过去6个月的数据
            current_month = normalize_datetime_for_db(datetime.now()).replace(day=1) - timedelta(days=i*30)
            month_start = current_month.replace(day=1)
            if current_month.month == 12:
                month_end = current_month.replace(year=current_month.year+1, month=1, day=1)
            else:
                month_end = current_month.replace(month=current_month.month+1, day=1)
            
            # 月份标签
            month_label = current_month.strftime('%Y-%m')
            months.append(month_label)
            
            # 活动数量
            monthly_activities_stmt = db.select(func.count()).select_from(Activity).filter(
                Activity.created_at.between(month_start, month_end)
            )
            monthly_activities = db.session.execute(monthly_activities_stmt).scalar() or 0
            activities_count.append(monthly_activities)
            
            # 报名数量
            monthly_registrations_stmt = db.select(func.count()).select_from(Registration).filter(
                Registration.register_time.between(month_start, month_end)
            )
            monthly_registrations = db.session.execute(monthly_registrations_stmt).scalar() or 0
            registrations_count.append(monthly_registrations)
        
        monthly_stats = {
            'labels': months,
            'activities': activities_count,
            'registrations': registrations_count
        }
        
        return jsonify({
            'registration_stats': registration_stats,
            'participation_stats': participation_stats,
            'monthly_stats': monthly_stats
        })
    except Exception as e:
        logger.error(f"Error in api_statistics: {e}")
        return jsonify({'error': '获取统计数据失败'}), 500

@admin_bp.route('/activity/<int:id>/registrations')
@admin_required
def activity_registrations(id):
    try:
        # 导入display_datetime函数供模板使用
        from src.utils.time_helpers import display_datetime
        activity = db.get_or_404(Activity, id)
        
        # 获取报名学生列表 - 修复报名详情查看问题
        # 使用SQLAlchemy查询，确保包含registration_id
        registrations = Registration.query.filter_by(
            activity_id=id
        ).join(
            User, Registration.user_id == User.id
        ).join(
            StudentInfo, User.id == StudentInfo.user_id
        ).add_columns(
            Registration.id.label('registration_id'),
            Registration.register_time,
            Registration.check_in_time,
            Registration.status,
            StudentInfo.real_name,
            StudentInfo.student_id,
            StudentInfo.grade,
            StudentInfo.college,
            StudentInfo.major,
            StudentInfo.phone,
            StudentInfo.points
        ).all()
        
        # 统计报名状态
        registered_count = db.session.execute(db.select(func.count()).select_from(Registration).filter_by(activity_id=id, status='registered')).scalar()
        cancelled_count = db.session.execute(db.select(func.count()).select_from(Registration).filter_by(activity_id=id, status='cancelled')).scalar()
        attended_count = db.session.execute(db.select(func.count()).select_from(Registration).filter_by(activity_id=id, status='attended')).scalar()
        
        # 修复签到状态统计 - 确保报名统计准确性
        # 这里处理签到后的状态计数，让前端能正确显示
        
        # 创建CSRF表单对象
        from flask_wtf import FlaskForm
        form = FlaskForm()
        
        return render_template('admin/activity_registrations.html',
                              activity=activity,
                              registrations=registrations,
                              registered_count=registered_count,
                              cancelled_count=cancelled_count,
                              attended_count=attended_count,
                              display_datetime=display_datetime,
                              form=form)
    except Exception as e:
        logger.error(f"Error in activity_registrations: {e}")
        flash('查看报名情况时出错', 'danger')
        return redirect(url_for('admin.activities'))

@admin_bp.route('/activity/<int:id>/export_excel')
@admin_required
def export_activity_registrations(id):
    try:
        activity = db.get_or_404(Activity, id)
        
        # 获取报名学生列表
        registrations = Registration.query.filter_by(
            activity_id=id
        ).join(
            User, Registration.user_id == User.id
        ).join(
            StudentInfo, User.id == StudentInfo.user_id
        ).add_columns(
            Registration.id.label('registration_id'),
            Registration.register_time,
            Registration.check_in_time,
            Registration.status,
            StudentInfo.real_name,
            StudentInfo.student_id,
            StudentInfo.grade,
            StudentInfo.college,
            StudentInfo.major,
            StudentInfo.phone,
            StudentInfo.points
        ).all()
        
        # 创建Excel文件
        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine='openpyxl')
        
        # 转换为DataFrame
        data = []
        for reg in registrations:
            # 将UTC时间转换为北京时间
            register_time_bj = localize_time(reg.register_time)
            check_in_time_bj = localize_time(reg.check_in_time) if reg.check_in_time else None
            
            data.append({
                '报名ID': reg.registration_id,
                '姓名': reg.real_name,
                '学号': reg.student_id,
                '年级': reg.grade,
                '学院': reg.college,
                '专业': reg.major,
                '手机号': reg.phone,
                '报名时间': register_time_bj.strftime('%Y-%m-%d %H:%M:%S') if register_time_bj else '',
                '状态': '已报名' if reg.status == 'registered' else '已取消' if reg.status == 'cancelled' else '已参加',
                '积分': reg.points or 0,
                '签到状态': '已签到' if reg.check_in_time else '未签到',
                '签到时间': check_in_time_bj.strftime('%Y-%m-%d %H:%M:%S') if check_in_time_bj else ''
            })
        
        df = pd.DataFrame(data)
        df.to_excel(writer, sheet_name='报名信息', index=False)
        
        # 保存Excel
        writer.close()
        output.seek(0)
        
        # 记录操作日志
        log_action('export_registrations', f'导出活动({activity.title})的报名信息')
        
        # 使用北京时间作为文件名
        beijing_now = get_beijing_time()
        
        # 返回Excel文件
        return send_file(
            output,
            as_attachment=True,
            download_name=f"{activity.title}_报名信息_{beijing_now.strftime('%Y%m%d%H%M%S')}.xlsx",
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        logger.error(f"Error exporting activity registrations: {e}")
        flash('导出报名信息时出错', 'danger')
        return redirect(url_for('admin.activity_registrations', id=id))

@admin_bp.route('/students/export_excel')
@admin_required
def export_students():
    try:
        # 获取所有学生信息
        students = User.query.filter_by(role_id=2).join(
            StudentInfo, User.id == StudentInfo.user_id
        ).add_columns(
            User.id,
            User.username,
            User.email,
            User.created_at,
            StudentInfo.real_name,
            StudentInfo.student_id,
            StudentInfo.grade,
            StudentInfo.college,
            StudentInfo.major,
            StudentInfo.phone,
            StudentInfo.qq,
            StudentInfo.points
        ).all()
        
        # 创建Excel文件
        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine='openpyxl')
        
        # 转换为DataFrame
        data = []
        for student in students:
            # 将UTC时间转换为北京时间
            beijing_created_at = localize_time(student.created_at)
            
            data.append({
                '用户ID': student.id,
                '用户名': student.username,
                '邮箱': student.email,
                '姓名': student.real_name,
                '学号': student.student_id,
                '年级': student.grade,
                '学院': student.college,
                '专业': student.major,
                '手机号': student.phone,
                'QQ': student.qq,
                '积分': student.points or 0,
                '注册时间': beijing_created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        df = pd.DataFrame(data)
        df.to_excel(writer, sheet_name='学生信息', index=False)
        
        # 保存Excel
        writer.close()
        output.seek(0)
        
        # 记录操作日志
        log_action('export_students', '导出所有学生信息')
        
        # 使用北京时间作为文件名
        beijing_now = get_beijing_time()
        
        # 返回Excel文件
        return send_file(
            output,
            as_attachment=True,
            download_name=f"学生信息_{beijing_now.strftime('%Y%m%d%H%M%S')}.xlsx",
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        logger.error(f"Error exporting students: {e}")
        flash('导出学生信息时出错', 'danger')
        return redirect(url_for('admin.students'))

@admin_bp.route('/backup', methods=['GET'])
@admin_required
def backup_system():
    try:
        backup_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backups')
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        backups = []
        for filename in os.listdir(backup_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(backup_dir, filename)
                backup_time = datetime.fromtimestamp(os.path.getctime(filepath))
                
                # 获取文件大小
                file_size = os.path.getsize(filepath)
                if file_size < 1024:
                    size_str = f"{file_size} B"
                elif file_size < 1024 * 1024:
                    size_str = f"{file_size / 1024:.1f} KB"
                else:
                    size_str = f"{file_size / (1024 * 1024):.1f} MB"
                
                # 尝试读取备份内容摘要
                content_summary = "未知内容"
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        content_parts = []
                        if 'data' in data:
                            if 'users' in data['data']:
                                content_parts.append(f"用户({len(data['data']['users'])})")
                            if 'activities' in data['data']:
                                content_parts.append(f"活动({len(data['data']['activities'])})")
                            if 'registrations' in data['data']:
                                content_parts.append(f"报名({len(data['data']['registrations'])})")
                            if 'tags' in data['data']:
                                content_parts.append(f"标签({len(data['data']['tags'])})")
                        
                        if content_parts:
                            content_summary = "、".join(content_parts)
                except:
                    pass
                
                backups.append({
                    'name': filename,
                    'created_at': backup_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'size': size_str,
                    'content': content_summary
                })
        
        backups.sort(key=lambda x: x['created_at'], reverse=True)
        
        return render_template('admin/backup.html',
                              backups=backups,
                              current_time=datetime.now().strftime('%Y%m%d_%H%M%S'))
    except Exception as e:
        logger.error(f"Error in backup system page: {e}")
        flash('加载备份系统页面时出错', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/backup/create', methods=['POST'])
@admin_required
def create_backup():
    try:
        backup_name = request.form.get('backup_name', f"backup_{normalize_datetime_for_db(datetime.now()).strftime('%Y%m%d_%H%M%S')}")
        include_users = 'include_users' in request.form
        include_activities = 'include_activities' in request.form
        include_registrations = 'include_registrations' in request.form
        backup_format = request.form.get('backup_format', 'json')  # 新增：备份格式选择
        
        # 准备备份数据
        backup_data = {
            'version': '1.0',
            'created_at': normalize_datetime_for_db(datetime.now()).isoformat(),
            'created_by': current_user.username,
            'data': {}
        }
        
        # 用户数据
        if include_users:
            backup_data['data']['users'] = [
                {
                    'username': user.username,
                    'email': user.email,
                    'role_id': user.role_id,
                    'active': user.active
                } for user in db.session.execute(db.select(User)).scalars().all()
            ]
            
            backup_data['data']['student_info'] = [
                {
                    'user_id': info.user_id,
                    'student_id': info.student_id,
                    'real_name': info.real_name,
                    'gender': info.gender,
                    'grade': info.grade,
                    'college': info.college,
                    'major': info.major,
                    'phone': info.phone,
                    'qq': info.qq,
                    'points': info.points,
                    'has_selected_tags': info.has_selected_tags
                } for info in db.session.execute(db.select(StudentInfo)).scalars().all()
            ]
        
        # 活动数据
        if include_activities:
            backup_data['data']['activities'] = [
                {
                    'title': activity.title,
                    'description': activity.description,
                    'location': activity.location,
                    'start_time': activity.start_time.isoformat() if activity.start_time else None,
                    'end_time': activity.end_time.isoformat() if activity.end_time else None,
                    'registration_deadline': activity.registration_deadline.isoformat() if activity.registration_deadline else None,
                    'max_participants': activity.max_participants,
                    'status': activity.status,
                    'type': activity.type,
                    'is_featured': activity.is_featured,
                    'points': activity.points,
                    'created_by': activity.created_by
                } for activity in db.session.execute(db.select(Activity)).scalars().all()
            ]
        
        # 报名数据
        if include_registrations:
            backup_data['data']['registrations'] = [
                {
                    'user_id': reg.user_id,
                    'activity_id': reg.activity_id,
                    'register_time': reg.register_time.isoformat() if reg.register_time else None,
                    'check_in_time': reg.check_in_time.isoformat() if reg.check_in_time else None,
                    'status': reg.status,
                    'remark': reg.remark
                } for reg in db.session.execute(db.select(Registration)).scalars().all()
            ]
        
        # 确保备份目录存在
        backup_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backups')
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        if backup_format == 'zip':
            # 创建ZIP格式备份
            filename = secure_filename(f"{backup_name}.zip")
            filepath = os.path.join(backup_dir, filename)
            
            # 创建临时JSON文件
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_json:
                json.dump(backup_data, temp_json, ensure_ascii=False, indent=2, default=str)
                temp_json_path = temp_json.name
            
            # 创建ZIP文件
            with zipfile.ZipFile(filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 添加JSON数据
                zipf.write(temp_json_path, arcname='backup_data.json')
                
                # 添加README文件
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_readme:
                    temp_readme.write(f"重庆师范大学师能素质协会系统备份\n")
                    temp_readme.write(f"创建时间: {normalize_datetime_for_db(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')}\n")
                    temp_readme.write(f"创建者: {current_user.username}\n\n")
                    temp_readme.write("备份内容:\n")
                    if include_users:
                        temp_readme.write(f"- 用户数据: {len(backup_data['data'].get('users', []))} 条记录\n")
                        temp_readme.write(f"- 学生信息: {len(backup_data['data'].get('student_info', []))} 条记录\n")
                    if include_activities:
                        temp_readme.write(f"- 活动数据: {len(backup_data['data'].get('activities', []))} 条记录\n")
                    if include_registrations:
                        temp_readme.write(f"- 报名数据: {len(backup_data['data'].get('registrations', []))} 条记录\n")
                    temp_readme_path = temp_readme.name
                
                zipf.write(temp_readme_path, arcname='README.txt')
                
                # 添加数据库文件副本
                db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'instance', 'cqnu_association.db')
                if os.path.exists(db_path):
                    zipf.write(db_path, arcname='database_backup.db')
            
            # 删除临时文件
            os.unlink(temp_json_path)
            os.unlink(temp_readme_path)
            
        else:
            # 创建JSON格式备份
            filename = secure_filename(f"{backup_name}.json")
            filepath = os.path.join(backup_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2, default=str)
        
        # 记录操作日志
        log_action('create_backup', f'创建系统备份: {filename}')
        
        flash(f'备份已创建: {filename}', 'success')
        return redirect(url_for('admin.backup_system'))
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating backup: {e}")
        flash(f'创建备份时出错: {str(e)}', 'danger')
        return redirect(url_for('admin.backup_system'))

@admin_bp.route('/backup/import', methods=['POST'])
@admin_required
def import_backup():
    try:
        if 'backup_file' not in request.files:
            flash('请选择备份文件', 'warning')
            return redirect(url_for('admin.backup_system'))
        
        file = request.files['backup_file']
        if file.filename == '':
            flash('未选择文件', 'warning')
            return redirect(url_for('admin.backup_system'))
        
        if not file.filename.endswith('.json'):
            flash('请上传.json格式的备份文件', 'warning')
            return redirect(url_for('admin.backup_system'))
        
        # 读取备份数据
        backup_data = json.load(file)
        
        # 开始数据导入
        if 'data' in backup_data:
            # 删除现有数据
            if 'registrations' in backup_data['data']:
                Registration.query.delete()
            
            if 'activities' in backup_data['data']:
                Activity.query.delete()
            
            if 'student_info' in backup_data['data']:
                StudentInfo.query.delete()
            
            if 'users' in backup_data['data']:
                User.query.delete()
            
            # 导入备份数据
            if 'users' in backup_data['data']:
                for user_data in backup_data['data']['users']:
                    user = User()
                    for key, value in user_data.items():
                        setattr(user, key, value)
                    db.session.add(user)
            
            if 'student_info' in backup_data['data']:
                for info_data in backup_data['data']['student_info']:
                    info = StudentInfo()
                    for key, value in info_data.items():
                        setattr(info, key, value)
                    db.session.add(info)
            
            if 'activities' in backup_data['data']:
                for activity_data in backup_data['data']['activities']:
                    activity = Activity()
                    for key, value in activity_data.items():
                        setattr(activity, key, value)
                    db.session.add(activity)
            
            if 'registrations' in backup_data['data']:
                for reg_data in backup_data['data']['registrations']:
                    reg = Registration()
                    for key, value in reg_data.items():
                        setattr(reg, key, value)
                    db.session.add(reg)
            
            db.session.commit()
            flash('备份数据导入成功', 'success')
            log_action('import_backup', '导入系统备份数据')
        else:
            flash('无效的备份文件格式', 'danger')
        
        return redirect(url_for('admin.backup_system'))
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error importing backup: {e}")
        flash('导入备份失败', 'danger')
        return redirect(url_for('admin.backup_system'))

# 添加更新报名状态的路由
@admin_bp.route('/registration/<int:id>/update_status', methods=['POST'])
@admin_required
def update_registration_status(id):
    try:
        registration = db.get_or_404(Registration, id)
        new_status = request.form.get('status')
        old_status = registration.status
        
        if new_status not in ['registered', 'cancelled', 'attended']:
            flash('无效的状态值', 'danger')
            return redirect(url_for('admin.activity_registrations', id=registration.activity_id))
        
        # 处理积分变更
        activity = db.session.get(Activity, registration.activity_id)
        student_info = StudentInfo.query.join(User).filter(User.id == registration.user_id).first()
        
        if student_info and activity:
            points = activity.points or (20 if activity.is_featured else 10)
            
            # 已参加 → 取消参加/已报名：扣除积分
            if old_status == 'attended' and new_status in ['registered', 'cancelled']:
                add_points(student_info.id, -points, f"取消参加活动：{activity.title}", activity.id)
                
            # 已报名/已取消 → 已参加：添加积分
            elif old_status in ['registered', 'cancelled'] and new_status == 'attended':
                add_points(student_info.id, points, f"参与活动：{activity.title}", activity.id)
        
        # 更新状态
        registration.status = new_status
        
        # 如果状态改为已参加，设置签到时间
        if new_status == 'attended' and not registration.check_in_time:
            registration.check_in_time = get_localized_now()
        # 如果从已参加改为其他状态，保留签到时间以便恢复
        
        db.session.commit()
        
        log_action('update_registration', f'更新报名状态: ID {id} 从 {old_status} 到 {new_status}')
        flash('报名状态已更新', 'success')
        return redirect(url_for('admin.activity_registrations', id=registration.activity_id))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating registration status: {e}")
        flash('更新报名状态时出错', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/activity/<int:id>/checkin', methods=['POST'])
@admin_required
def activity_checkin(id):
    try:
        student_id = request.form.get('student_id')
        if not student_id:
            return jsonify({'success': False, 'message': '学生ID不能为空'})
        
        # 查找学生
        student = db.session.execute(db.select(StudentInfo).filter_by(student_id=student_id)).scalar_one_or_none()
        if not student:
            return jsonify({'success': False, 'message': '学生不存在'})
        
        # 查找活动
        activity = db.get_or_404(Activity, id)
        
        # 查找报名记录
        registration = db.session.execute(db.select(Registration).filter_by(
            user_id=student.user_id,
            activity_id=id
        )).scalar_one_or_none()
        
        if not registration:
            return jsonify({'success': False, 'message': '该学生未报名此活动'})
        
        if registration.check_in_time:
            return jsonify({'success': False, 'message': '该学生已签到'})
        
        # 更新签到状态
        registration.status = 'attended'
        registration.check_in_time = get_localized_now()
        
        # 添加积分奖励
        points = activity.points or (20 if activity.is_featured else 10)  # 使用活动自定义积分或默认值
        student_info = db.session.execute(db.select(StudentInfo).filter_by(user_id=student.user_id)).scalar_one_or_none()
        if student_info:
            if add_points(student_info.id, points, f"参与活动：{activity.title}", activity.id):
                db.session.commit()
                return jsonify({
                    'success': True, 
                    'message': f'签到成功！获得 {points} 积分',
                    'points': points
                })
        
        return jsonify({'success': False, 'message': '签到失败，请重试'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in activity checkin: {e}")
        return jsonify({'success': False, 'message': '签到时出错'})

@admin_bp.route('/tags')
@admin_required
def manage_tags():
    from src.utils.time_helpers import display_datetime
    
    tags_stmt = db.select(Tag).order_by(Tag.created_at.desc())
    tags = db.session.execute(tags_stmt).scalars().all()
    return render_template('admin/tags.html', tags=tags, display_datetime=display_datetime)

@admin_bp.route('/tags/create', methods=['POST'])
@admin_required
def create_tag():
    try:
        name = request.form.get('name', '').strip()
        color = request.form.get('color', 'primary')
        
        if not name:
            flash('标签名称不能为空', 'danger')
            return redirect(url_for('admin.manage_tags'))
        
        # 检查是否已存在
        tag_stmt = db.select(Tag).filter_by(name=name)
        existing_tag = db.session.execute(tag_stmt).scalar_one_or_none()
        if existing_tag:
            flash('标签已存在', 'warning')
            return redirect(url_for('admin.manage_tags'))
        
        tag = Tag(name=name, color=color)
        db.session.add(tag)
        db.session.commit()
        
        flash('标签创建成功', 'success')
        log_action('create_tag', f'创建标签: {name}')
        return redirect(url_for('admin.manage_tags'))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating tag: {e}")
        flash('创建标签失败', 'danger')
        return redirect(url_for('admin.manage_tags'))

@admin_bp.route('/tags/<int:id>/edit', methods=['POST'])
@admin_required
def edit_tag(id):
    try:
        tag = db.get_or_404(Tag, id)
        name = request.form.get('name', '').strip()
        color = request.form.get('color', 'primary')
        
        if not name:
            flash('标签名称不能为空', 'danger')
            return redirect(url_for('admin.manage_tags'))
        
        # 检查新名称是否与其他标签重复
        check_stmt = db.select(Tag).filter(Tag.name == name, Tag.id != id)
        existing_tag = db.session.execute(check_stmt).scalar_one_or_none()
        if existing_tag:
            flash('标签名称已存在', 'warning')
            return redirect(url_for('admin.manage_tags'))
        
        tag.name = name
        tag.color = color
        db.session.commit()
        
        flash('标签更新成功', 'success')
        log_action('edit_tag', f'编辑标签: {name}')
        return redirect(url_for('admin.manage_tags'))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error editing tag: {e}")
        flash('更新标签失败', 'danger')
        return redirect(url_for('admin.manage_tags'))

@admin_bp.route('/tags/<int:id>/delete', methods=['POST'])
@admin_required
def delete_tag(id):
    try:
        validate_csrf(request.form.get('csrf_token'))
        tag = db.get_or_404(Tag, id)
        name = tag.name
        
        # 从所有相关活动中移除标签
        for activity in tag.activities:
            activity.tags.remove(tag)
        
        db.session.delete(tag)
        db.session.commit()
        
        log_action('delete_tag', f'删除标签: {name}')
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting tag: {e}")
        return jsonify({'success': False, 'message': '删除标签失败'})

@admin_bp.route('/api/statistics_ext')
@admin_bp.route('/admin/api/statistics_ext')  # 添加一个包含admin前缀的路由
@admin_required
def api_statistics_ext():
    try:
        # 标签热度 - 改为统计学生选择的标签而非活动标签
        from src.models import Tag, StudentInfo, student_tags
        
        tag_stats_stmt = db.select(
            Tag.name, 
            func.count(student_tags.c.student_id).label('count')
        ).outerjoin(
            student_tags, Tag.id == student_tags.c.tag_id
        ).group_by(Tag.id)
        
        tag_stats = db.session.execute(tag_stats_stmt).all()
        
        tag_heat = {
            'labels': [t[0] for t in tag_stats],
            'data': [t[1] for t in tag_stats]
        }
        
        # 积分分布
        from src.models import StudentInfo
        points_bins = [0, 10, 30, 50, 100, 200, 500, 1000]
        bin_labels = [f'{points_bins[i]}-{points_bins[i+1]-1}' for i in range(len(points_bins)-1)] + [f'{points_bins[-1]}+']
        bin_counts = [0] * len(bin_labels)  # 修正：使用bin_labels的长度
        
        student_info_stmt = db.select(StudentInfo)
        students = db.session.execute(student_info_stmt).scalars().all()
        
        for stu in students:
            points = stu.points or 0  # 处理None值
            
            # 检查最后一个区间（特殊情况）
            if points >= points_bins[-1]:
                bin_counts[-1] += 1
                continue
                
            # 检查其他区间
            for i in range(len(points_bins) - 1):
                if points_bins[i] <= points < points_bins[i+1]:
                    bin_counts[i] += 1
                    break
        
        points_dist = {
            'labels': bin_labels,
            'data': bin_counts
        }
        
        # 添加注册趋势数据（每日新注册用户数）
        try:
            now = get_localized_now()
            days_ago_30 = now - timedelta(days=30)
            
            registration_trend_stmt = db.select(
                func.date(User.created_at).label('date'),
                func.count(User.id).label('count')
            ).filter(
                User.created_at >= days_ago_30
            ).group_by(
                func.date(User.created_at)
            )
            
            registration_trend = db.session.execute(registration_trend_stmt).all()
            
            # 将结果转换为前端可用的格式
            reg_dates = [(days_ago_30 + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(31)]
            reg_counts = [0] * 31
            
            for item in registration_trend:
                date_str = item.date.strftime('%Y-%m-%d') if hasattr(item.date, 'strftime') else str(item.date)
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    day_diff = (date_obj - days_ago_30).days
                    if 0 <= day_diff < 31:
                        reg_counts[day_diff] = item.count
                except:
                    pass
            
            registration_trend_data = {
                'labels': reg_dates,
                'data': reg_counts
            }
        except Exception as e:
            logger.error(f"获取注册趋势数据失败: {e}")
            registration_trend_data = {
                'labels': [],
                'data': []
            }
        
        return jsonify({
            'tag_heat': tag_heat, 
            'points_dist': points_dist,
            'registration_trend': registration_trend_data
        })
    except Exception as e:
        logger.error(f"Error in api_statistics_ext: {e}")
        return jsonify({'error': '获取扩展统计数据失败'}), 500

@admin_bp.route('/activity/<int:id>/reviews')
@admin_required
def activity_reviews(id):
    try:
        from src.models import Activity, ActivityReview
        from src.utils.time_helpers import display_datetime
        from flask_wtf.csrf import generate_csrf
        
        activity = db.get_or_404(Activity, id)
        reviews = ActivityReview.query.filter_by(activity_id=id).order_by(ActivityReview.created_at.desc()).all()
        if reviews:
            average_rating = sum(r.rating for r in reviews) / len(reviews)
        else:
            average_rating = 0
        
        # 创建CSRF表单对象
        from flask_wtf import FlaskForm
        form = FlaskForm()
        
        return render_template('admin/activity_reviews.html', 
                            activity=activity, 
                            reviews=reviews, 
                            average_rating=average_rating,
                            display_datetime=display_datetime,
                            form=form)
    except Exception as e:
        logger.error(f"Error in activity_reviews: {str(e)}")
        flash('查看活动评价时出错', 'danger')
        return redirect(url_for('admin.activities'))

@admin_bp.route('/api/qrcode/checkin/<int:id>')
@admin_required
def generate_checkin_qrcode(id):
    try:
        # 检查活动是否存在
        activity = db.get_or_404(Activity, id)
        
        # 获取当前本地化时间
        now = get_beijing_time()
        
        # 生成唯一签到密钥，确保时效性和安全性
        checkin_key = hashlib.sha256(f"{activity.id}:{now.timestamp()}:{current_app.config['SECRET_KEY']}".encode()).hexdigest()[:16]
        
        # 优先使用数据库存储
        try:
            activity.checkin_key = checkin_key
            activity.checkin_key_expires = now + timedelta(minutes=5)  # 5分钟有效期
            db.session.commit()
        except Exception as e:
            logger.error(f"无法存储签到密钥到数据库: {e}")
            # 如果数据库存储失败，记录错误但继续生成二维码
            pass
        
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
        
        # 保存到内存并转为base64
        img_buffer = BytesIO()
        qr_image.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        qr_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
        
        # 返回JSON格式的二维码数据，包含data:image/png;base64前缀
        return jsonify({
            'success': True,
            'qrcode': f"data:image/png;base64,{qr_base64}",
            'expires_in': 300,  # 5分钟，单位秒
            'generated_at': now.strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        logger.error(f"生成签到二维码时出错: {e}")
        return jsonify({'success': False, 'message': '生成二维码失败'}), 500

@admin_bp.route('/checkin-modal/<int:activity_id>')
@login_required
@admin_required
def checkin_modal(activity_id):
    """签到管理界面"""
    try:
        # 记录开始调试信息
        logger.info(f"进入checkin_modal函数: activity_id={activity_id}")
        
        # 生成CSRF令牌
        from flask_wtf.csrf import generate_csrf
        csrf_token = generate_csrf()
        logger.info(f"生成CSRF令牌: {csrf_token[:10]}...")
        
        # 导入display_datetime函数
        from src.utils.time_helpers import display_datetime
        logger.info(f"导入display_datetime函数: 类型={type(display_datetime)}")
        
        # 添加调试日志
        logger.info(f"display_datetime类型: {type(display_datetime)}, 值: {display_datetime}")
        
        # 获取活动信息
        activity = db.get_or_404(Activity, activity_id)
        logger.info(f"获取活动信息: id={activity.id}, 标题={activity.title}")
        
        # 获取当前时间
        now = get_beijing_time()
        logger.info(f"获取当前北京时间: {now}")
        
        # 获取报名人数
        registration_count = Registration.query.filter(
            Registration.activity_id == activity_id,
            db.or_(
                Registration.status == 'registered',
                Registration.status == 'attended'
            )
        ).count()
        logger.info(f"获取报名人数: {registration_count}")
        
        # 获取签到人数
        checkin_count = Registration.query.filter(
            Registration.activity_id == activity_id,
            Registration.check_in_time.isnot(None)
        ).count()
        logger.info(f"获取签到人数: {checkin_count}")
        
        # 获取签到记录
        checkins = db.session.query(
            Registration.id,
            StudentInfo.student_id,
            StudentInfo.real_name,
            StudentInfo.college,
            StudentInfo.major,
            Registration.check_in_time
        ).join(
            StudentInfo, Registration.user_id == StudentInfo.user_id
        ).filter(
            Registration.activity_id == activity_id,
            Registration.check_in_time.isnot(None)
        ).all()
        logger.info(f"获取签到记录: {len(checkins)}条")
        
        # 日志记录
        logger.info(f"管理员访问签到模态框: 活动ID={activity_id}, 报名人数={registration_count}, 签到人数={checkin_count}")
        
        
        return render_template(
            'admin/checkin_modal.html',
            activity=activity,
            registration_count=registration_count,
            checkin_count=checkin_count,
            checkins=checkins,
            now=now,
            display_datetime=display_datetime
        )
        
    except Exception as e:
        logger.error(f"签到模态框加载失败: {str(e)}", exc_info=True)
        flash('加载签到管理界面失败', 'danger')
        return redirect(url_for('admin.activities'))

@admin_bp.route('/checkin-modal/<int:id>')
@login_required
@admin_required
def checkin_modal_id(id):
    """兼容旧版路由，重定向到新版签到模态框"""
    return redirect(url_for('admin.checkin_modal', activity_id=id))

@admin_bp.route('/admin/checkin-modal/<int:id>')
@login_required
@admin_required
def checkin_modal_admin(id):
    """兼容带admin前缀的路由，重定向到新版签到模态框"""
    return redirect(url_for('admin.checkin_modal', activity_id=id))

# 切换活动签到状态
@admin_bp.route('/activity/<int:id>/toggle-checkin', methods=['POST'])
@admin_required
def toggle_checkin(id):
    try:
        # 验证CSRF令牌（增加更详细的错误处理）
        try:
            from flask_wtf.csrf import validate_csrf
            # 尝试从表单中获取CSRF令牌
            csrf_token = request.form.get('csrf_token')
            if not csrf_token:
                # 如果表单中没有CSRF令牌，尝试从请求头获取
                csrf_token = request.headers.get('X-CSRFToken')
            
            if not csrf_token:
                logger.warning("未找到CSRF令牌")
                flash('操作失败，缺少安全验证令牌', 'danger')
                return redirect(url_for('admin.activity_view', id=id))
            
            # 验证CSRF令牌
            validate_csrf(csrf_token)
        except Exception as csrf_error:
            logger.warning(f"CSRF验证失败: {csrf_error}")
            # 暂时允许请求继续处理，但记录错误
            # 您可以根据需要取消下面的注释以强制执行CSRF验证
            # flash('安全验证失败，请刷新页面重试', 'danger')
            # return redirect(url_for('admin.activity_view', id=id))
        
        activity = db.get_or_404(Activity, id)
        
        # 获取当前状态
        current_status = getattr(activity, 'checkin_enabled', False)
        
        # 切换状态（取反）
        new_status = not current_status
        activity.checkin_enabled = new_status
        
        # 如果开启签到，生成或更新签到密钥
        if new_status:
            now = get_localized_now()
            checkin_key = hashlib.sha256(f"{activity.id}:{now.timestamp()}:{current_app.config['SECRET_KEY']}".encode()).hexdigest()[:16]
            activity.checkin_key = checkin_key
            activity.checkin_key_expires = now + timedelta(hours=24)  # 24小时有效期
            status_text = "开启"
        else:
            status_text = "关闭"
        
        db.session.commit()
        
        # 记录新状态
        flash(f'已{status_text}活动签到', 'success')
        
        # 记录操作日志
        log_action(f'toggle_checkin_{status_text}', f'管理员{status_text}了活动 {activity.title} 的签到')
        
        # 重定向回原页面
        referrer = request.referrer
        if referrer:
            # 修复：检查是否在checkin_modal页面
            if 'checkin-modal' in referrer:
                return redirect(url_for('admin.checkin_modal_id', id=id))
            # 检查是否有其他特殊页面
            elif '/admin/activity/' in referrer and '/view' in referrer:
                return redirect(url_for('admin.activity_view', id=id))
            # 否则返回到原始页面
            return redirect(referrer)
        
        # 如果没有referrer，默认回到活动详情页
        return redirect(url_for('admin.activity_view', id=id))
    except Exception as e:
        db.session.rollback()
        logger.error(f"切换签到状态失败: {e}")
        flash('操作失败，请重试', 'danger')
        return redirect(url_for('admin.activity_view', id=id))

# 系统日志页面
@admin_bp.route('/system_logs', methods=['GET'])
@admin_required
def system_logs():
    try:
        # 获取日志文件内容
        log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'cqnu_association.log')
        logs = []
        
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                # 读取最后1000行日志
                logs = f.readlines()[-1000:]
        
        # 倒序显示日志（最新的在前面）
        logs.reverse()
        
        return render_template('admin/system_logs.html', logs=logs)
    except Exception as e:
        logger.error(f"Error in system logs page: {e}")
        flash('加载系统日志时出错', 'danger')
        return redirect(url_for('admin.dashboard'))

# 下载日志
@admin_bp.route('/download_logs', methods=['GET'])
@admin_required
def download_logs():
    try:
        log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'cqnu_association.log')
        
        if not os.path.exists(log_file):
            flash('日志文件不存在', 'warning')
            return redirect(url_for('admin.system_logs'))
        
        # 记录操作日志
        log_action('download_logs', '下载系统日志文件')
        
        # 返回文件下载
        return send_file(
            log_file,
            mimetype='text/plain',
            as_attachment=True,
            download_name=f'system_logs_{normalize_datetime_for_db(datetime.now()).strftime("%Y%m%d_%H%M%S")}.log'
        )
    except Exception as e:
        logger.error(f"Error downloading logs: {e}")
        flash('下载日志文件时出错', 'danger')
        return redirect(url_for('admin.system_logs'))

# 清空日志
@admin_bp.route('/clear_logs', methods=['POST'])
@admin_required
def clear_logs():
    try:
        log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'cqnu_association.log')
        
        if os.path.exists(log_file):
            # 清空日志文件内容
            with open(log_file, 'w') as f:
                f.write(f"日志已于 {normalize_datetime_for_db(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} 被管理员清空\n")
        
        # 记录操作日志
        log_action('clear_logs', '清空系统日志')
        
        flash('日志已清空', 'success')
        return redirect(url_for('admin.system_logs'))
    except Exception as e:
        logger.error(f"Error clearing logs: {e}")
        flash('清空日志时出错', 'danger')
        return redirect(url_for('admin.system_logs'))

# 下载备份文件
@admin_bp.route('/backup/download/<path:filename>', methods=['GET'])
@admin_required
def download_backup(filename):
    try:
        backup_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backups')
        
        # 安全检查：确保文件名不包含路径遍历
        if '..' in filename or filename.startswith('/'):
            flash('无效的文件名', 'danger')
            return redirect(url_for('admin.backup_system'))
        
        filepath = os.path.join(backup_dir, filename)
        
        if not os.path.exists(filepath):
            flash('备份文件不存在', 'warning')
            return redirect(url_for('admin.backup_system'))
        
        # 记录操作日志
        log_action('download_backup', f'下载备份文件: {filename}')
        
        # 返回文件下载
        return send_file(
            filepath,
            mimetype='application/json',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        logger.error(f"Error downloading backup: {e}")
        flash('下载备份文件时出错', 'danger')
        return redirect(url_for('admin.backup_system'))

# 删除备份文件
@admin_bp.route('/backup/delete/<path:filename>', methods=['GET'])
@admin_required
def delete_backup(filename):
    try:
        backup_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backups')
        
        # 安全检查：确保文件名不包含路径遍历
        if '..' in filename or filename.startswith('/'):
            flash('无效的文件名', 'danger')
            return redirect(url_for('admin.backup_system'))
        
        filepath = os.path.join(backup_dir, filename)
        
        if not os.path.exists(filepath):
            flash('备份文件不存在', 'warning')
            return redirect(url_for('admin.backup_system'))
        
        # 删除文件
        os.remove(filepath)
        
        # 记录操作日志
        log_action('delete_backup', f'删除备份文件: {filename}')
        
        flash('备份文件已删除', 'success')
        return redirect(url_for('admin.backup_system'))
    except Exception as e:
        logger.error(f"Error deleting backup: {e}")
        flash('删除备份文件时出错', 'danger')
        return redirect(url_for('admin.backup_system'))

# 重置系统数据
@admin_bp.route('/reset_system', methods=['GET'])
@admin_required
def reset_system_page():
    try:
        return render_template('admin/reset_system.html')
    except Exception as e:
        logger.error(f"Error in reset system page: {e}")
        flash('加载重置系统页面时出错', 'danger')
        return redirect(url_for('admin.dashboard'))

# 执行系统重置
@admin_bp.route('/reset_system', methods=['POST'])
@admin_required
def reset_system():
    try:
        # 验证管理员密码
        password = request.form.get('admin_password')
        if not current_user.check_password(password):
            flash('管理员密码错误，无法执行重置操作', 'danger')
            return redirect(url_for('admin.reset_system_page'))
        
        # 获取重置选项
        reset_users = 'reset_users' in request.form
        reset_activities = 'reset_activities' in request.form
        reset_registrations = 'reset_registrations' in request.form
        reset_tags = 'reset_tags' in request.form
        reset_logs = 'reset_logs' in request.form
        
        # 创建备份
        backup_name = f"pre_reset_{normalize_datetime_for_db(datetime.now()).strftime('%Y%m%d_%H%M%S')}"
        backup_data = {'data': {}}
        
        # 备份用户数据
        if reset_users:
            backup_data['data']['users'] = [
                {
                    'username': user.username,
                    'email': user.email,
                    'role_id': user.role_id,
                    'active': user.active
                } for user in db.session.execute(db.select(User)).scalars().all()
            ]
            backup_data['data']['student_info'] = [
                {
                    'user_id': info.user_id,
                    'student_id': info.student_id,
                    'real_name': info.real_name,
                    'gender': info.gender,
                    'grade': info.grade,
                    'college': info.college,
                    'major': info.major,
                    'phone': info.phone,
                    'qq': info.qq,
                    'points': info.points,
                    'has_selected_tags': info.has_selected_tags
                } for info in db.session.execute(db.select(StudentInfo)).scalars().all()
            ]
        
        # 备份活动数据
        if reset_activities:
            backup_data['data']['activities'] = [
                {
                    'title': activity.title,
                    'description': activity.description,
                    'location': activity.location,
                    'start_time': activity.start_time.isoformat() if activity.start_time else None,
                    'end_time': activity.end_time.isoformat() if activity.end_time else None,
                    'registration_deadline': activity.registration_deadline.isoformat() if activity.registration_deadline else None,
                    'max_participants': activity.max_participants,
                    'status': activity.status,
                    'type': activity.type,
                    'is_featured': activity.is_featured,
                    'points': activity.points,
                    'created_by': activity.created_by
                } for activity in db.session.execute(db.select(Activity)).scalars().all()
            ]
        
        # 备份报名数据
        if reset_registrations:
            backup_data['data']['registrations'] = [
                {
                    'user_id': reg.user_id,
                    'activity_id': reg.activity_id,
                    'register_time': reg.register_time.isoformat() if reg.register_time else None,
                    'check_in_time': reg.check_in_time.isoformat() if reg.check_in_time else None,
                    'status': reg.status,
                    'remark': reg.remark
                } for reg in db.session.execute(db.select(Registration)).scalars().all()
            ]
        
        # 备份标签数据
        if reset_tags:
            backup_data['data']['tags'] = [
                {
                    'name': tag.name,
                    'description': tag.description,
                    'color': tag.color
                } for tag in db.session.execute(db.select(Tag)).scalars().all()
            ]
        
        # 保存备份文件
        backup_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backups')
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        filename = secure_filename(f"{backup_name}.json")
        filepath = os.path.join(backup_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2, default=str)
        
        # 执行重置操作
        if reset_registrations:
            Registration.query.delete()
            db.session.commit()
            flash('所有报名记录已重置', 'success')
        
        if reset_activities:
            # 先清除活动标签关联
            db.session.execute(activity_tags.delete())
            db.session.commit()
            
            # 清除积分历史中对活动的引用
            PointsHistory.query.filter(PointsHistory.activity_id.isnot(None)).delete()
            db.session.commit()
            
            # 删除活动评价
            from src.models import ActivityReview
            ActivityReview.query.delete()
            db.session.commit()
            
            # 删除活动
            Activity.query.delete()
            db.session.commit()
            flash('所有活动已重置', 'success')
        
        if reset_tags:
            # 清除标签关联
            db.session.execute(student_tags.delete())
            db.session.execute(activity_tags.delete())
            db.session.commit()
            
            # 删除标签
            Tag.query.delete()
            db.session.commit()
            flash('所有标签已重置', 'success')
            
            # 重新创建默认标签
            default_tags = [
                {'name': '讲座', 'color': 'primary', 'description': '各类学术讲座'},
                {'name': '研讨会', 'color': 'info', 'description': '小组研讨活动'},
                {'name': '实践活动', 'color': 'success', 'description': '校内外实践活动'},
                {'name': '志愿服务', 'color': 'danger', 'description': '志愿者服务活动'},
                {'name': '文体活动', 'color': 'warning', 'description': '文化体育类活动'},
                {'name': '竞赛', 'color': 'secondary', 'description': '各类竞赛活动'}
            ]
            
            for tag_data in default_tags:
                tag = Tag(name=tag_data['name'], color=tag_data['color'], description=tag_data['description'])
                db.session.add(tag)
            
            db.session.commit()
            flash('默认标签已重新创建', 'success')
        
        if reset_users:
            # 保留当前管理员账号
            admin_username = current_user.username
            admin_email = current_user.email
            admin_password = current_user.password_hash
            
            try:
                # 删除所有用户相关数据 - 按照正确的顺序处理外键依赖
                # 首先删除积分历史记录
                logger.info("删除积分历史记录")
                PointsHistory.query.delete()
                db.session.commit()
                
                # 然后删除学生信息
                logger.info("删除学生信息")
                StudentInfo.query.delete()
                db.session.commit()
                
                # 最后删除用户账号（除了当前管理员）
                logger.info("删除用户账号")
                User.query.filter(User.id != current_user.id).delete()
                db.session.commit()
                
                # 重新创建角色
                admin_role = db.session.execute(db.select(Role).filter_by(name='Admin')).scalar_one_or_none()
                if not admin_role:
                    admin_role = Role(name='Admin', description='管理员')
                    db.session.add(admin_role)
                
                student_role = db.session.execute(db.select(Role).filter_by(name='Student')).scalar_one_or_none()
                if not student_role:
                    student_role = Role(name='Student', description='学生')
                    db.session.add(student_role)
                
                db.session.commit()
                
                flash('用户数据已重置，管理员账号已保留', 'success')
            except Exception as e:
                db.session.rollback()
                logger.error(f"重置用户数据时出错: {str(e)}")
                flash(f'重置用户数据时出错: {str(e)}', 'danger')
        
        
        if reset_logs:
            # 清空日志文件
            log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'cqnu_association.log')
            if os.path.exists(log_file):
                with open(log_file, 'w') as f:
                    f.write(f"日志已于 {normalize_datetime_for_db(datetime.now()).strftime('%Y-%m-%d %H:%M:%S')} 被管理员重置\n")
            
            # 清空系统日志表
            SystemLog.query.delete()
            db.session.commit()
            
            flash('系统日志已重置', 'success')
        
        # 记录操作日志
        log_action('reset_system', f'系统重置，选项：用户={reset_users}，活动={reset_activities}，报名={reset_registrations}，标签={reset_tags}，日志={reset_logs}')
        
        flash(f'系统重置已完成，备份已保存为 {filename}', 'success')
        return redirect(url_for('admin.dashboard'))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error resetting system: {e}")
        flash(f'重置系统时出错: {str(e)}', 'danger')
        return redirect(url_for('admin.reset_system_page'))

@admin_bp.route('/notifications')
@admin_required
def notifications():
    try:
        page = request.args.get('page', 1, type=int)
        notifications = Notification.query.order_by(Notification.created_at.desc()).paginate(page=page, per_page=10)
        
        # 确保display_datetime函数在模板中可用
        return render_template('admin/notifications.html', 
                              notifications=notifications,
                              display_datetime=display_datetime)
    except Exception as e:
        logger.error(f"Error in notifications page: {e}")
        flash('加载通知列表时出错', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/notification/create', methods=['GET', 'POST'])
@admin_required
def create_notification():
    try:
        # 创建Flask-WTF表单对象
        from flask_wtf import FlaskForm
        
        form = FlaskForm()
        
        if request.method == 'POST':
            title = request.form.get('title')
            content = request.form.get('content')
            is_important = 'is_important' in request.form
            expiry_date_str = request.form.get('expiry_date')
            
            if not title or not content:
                flash('标题和内容不能为空', 'danger')
                return redirect(url_for('admin.create_notification'))
            
            # 处理过期日期
            expiry_date = None
            if expiry_date_str:
                try:
                    expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d')
                    # 确保时区信息正确
                    expiry_date = pytz.utc.localize(expiry_date)
                except ValueError:
                    flash('日期格式无效', 'danger')
                    return redirect(url_for('admin.create_notification'))
            
            # 创建通知 - 使用UTC时间
            now = pytz.utc.localize(datetime.utcnow())
            
            notification = Notification(
                title=title,
                content=content,
                is_important=is_important,
                created_at=now,
                created_by=current_user.id,
                expiry_date=expiry_date,
                is_public=True  # 默认为公开通知
            )
            
            db.session.add(notification)
            db.session.commit()
            
            log_action('create_notification', f'创建通知: {title}')
            flash('通知创建成功', 'success')
            return redirect(url_for('admin.notifications'))
        
        return render_template('admin/notification_form.html', title='创建通知', form=form)
    except Exception as e:
        logger.error(f"Error in create_notification: {e}")
        flash('创建通知时出错', 'danger')
        return redirect(url_for('admin.notifications'))

@admin_bp.route('/notification/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_notification(id):
    try:
        notification = db.get_or_404(Notification, id)
        
        # 创建Flask-WTF表单对象
        from flask_wtf import FlaskForm
        
        form = FlaskForm()
        
        if request.method == 'POST':
            title = request.form.get('title')
            content = request.form.get('content')
            is_important = 'is_important' in request.form
            expiry_date_str = request.form.get('expiry_date')
            
            if not title or not content:
                flash('标题和内容不能为空', 'danger')
                return redirect(url_for('admin.edit_notification', id=id))
            
            # 处理过期日期
            if expiry_date_str:
                try:
                    expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d')
                    expiry_date = ensure_timezone_aware(expiry_date)
                    notification.expiry_date = expiry_date
                except ValueError:
                    flash('日期格式无效', 'danger')
                    return redirect(url_for('admin.edit_notification', id=id))
            else:
                notification.expiry_date = None
            
            # 更新通知
            notification.title = title
            notification.content = content
            notification.is_important = is_important
            
            db.session.commit()
            
            log_action('edit_notification', f'编辑通知: {title}')
            flash('通知更新成功', 'success')
            return redirect(url_for('admin.notifications'))
        
        # 格式化日期用于表单显示
        expiry_date = ''
        if notification.expiry_date:
            expiry_date = notification.expiry_date.strftime('%Y-%m-%d')
        
        return render_template('admin/notification_form.html', 
                              notification=notification,
                              expiry_date=expiry_date,
                              title='编辑通知',
                              form=form)
    except Exception as e:
        logger.error(f"Error in edit_notification: {e}")
        flash('编辑通知时出错', 'danger')
        return redirect(url_for('admin.notifications'))

@admin_bp.route('/notification/<int:id>/delete', methods=['POST'])
@admin_required
def delete_notification(id):
    try:
        notification = db.get_or_404(Notification, id)
        
        # 删除所有关联的已读记录
        db.session.execute(db.delete(NotificationRead).filter_by(notification_id=id))
        
        # 删除通知
        db.session.delete(notification)
        db.session.commit()
        
        log_action(
            action='delete_notification', 
            details=f'删除通知: {notification.title}'
        )
        flash('通知已删除', 'success')
        return redirect(url_for('admin.notifications'))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in delete_notification: {e}")
        flash('删除通知时出错', 'danger')
        return redirect(url_for('admin.notifications'))

@admin_bp.route('/messages')
@admin_required
def messages():
    try:
        # 记录日志
        logger.info("开始加载管理员站内信页面")
        logger.info(f"当前用户ID: {current_user.id}, 用户名: {current_user.username}")
        
        page = request.args.get('page', 1, type=int)
        filter_type = request.args.get('filter', 'all')
        
        logger.info(f"过滤类型: {filter_type}, 页码: {page}")
        
        # 检查数据库中是否存在消息
        total_messages = db.session.execute(db.select(func.count()).select_from(Message)).scalar()
        logger.info(f"数据库中总消息数: {total_messages}")
        
        # 检查当前用户的消息
        sent_count = db.session.execute(db.select(func.count()).select_from(Message).filter_by(sender_id=current_user.id)).scalar()
        received_count = db.session.execute(db.select(func.count()).select_from(Message).filter_by(receiver_id=current_user.id)).scalar()
        logger.info(f"当前用户发送的消息: {sent_count}, 接收的消息: {received_count}")
        
        # 检查是否有可用的接收者
        available_receivers = db.session.execute(db.select(func.count()).select_from(User).filter(User.id != current_user.id)).scalar()
        if available_receivers == 0:
            flash('系统中没有其他用户，无法发送消息', 'warning')
            logger.warning("系统中没有可用的消息接收者")
        
        # 根据过滤类型查询消息
        if filter_type == 'sent':
            logger.info("查询已发送消息")
            query = Message.query.filter_by(sender_id=current_user.id)
        elif filter_type == 'received':
            logger.info("查询已接收消息")
            query = Message.query.filter_by(receiver_id=current_user.id)
        else:  # 'all'
            logger.info("查询所有消息")
            # 使用显式导入的or_
            from sqlalchemy import or_
            query = Message.query.filter(or_(
                Message.sender_id == current_user.id,
                Message.receiver_id == current_user.id
            ))
        
        logger.info("执行分页查询")
        messages = query.order_by(Message.created_at.desc()).paginate(page=page, per_page=10)
        logger.info(f"查询到消息数量: {len(messages.items) if messages else 0}")
        
        # 检查每条消息的详细信息
        if messages and messages.items:
            for i, msg in enumerate(messages.items):
                logger.info(f"消息 {i+1}: ID={msg.id}, 主题={msg.subject}, 发送者ID={msg.sender_id}, 接收者ID={msg.receiver_id}, 时间={msg.created_at}")
        
        logger.info("渲染站内信模板")
        # 导入display_datetime函数供模板使用
        from src.utils.time_helpers import display_datetime
        
        return render_template('admin/messages.html', 
                              messages=messages, 
                              filter_type=filter_type,
                              no_receivers=(available_receivers == 0),
                              display_datetime=display_datetime)
    except Exception as e:
        logger.error(f"Error in messages page: {str(e)}")
        import traceback
        logger.error(f"详细错误信息: {traceback.format_exc()}")
        flash('加载消息列表时出错', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/message/create', methods=['GET', 'POST'])
@admin_required
def create_message():
    try:
        logger.info("开始创建站内信")
        
        # 创建一个空表单对象用于CSRF保护
        from flask_wtf import FlaskForm
        form = FlaskForm()
        
        if request.method == 'POST':
            receiver_id = request.form.get('receiver_id')
            subject = request.form.get('subject')
            content = request.form.get('content')
            
            if not receiver_id or not subject or not content:
                flash('收件人、主题和内容不能为空', 'danger')
                return redirect(url_for('admin.create_message'))
            
            # 验证接收者是否存在
            receiver = db.session.get(User, receiver_id)
            if not receiver:
                flash('收件人不存在', 'danger')
                return redirect(url_for('admin.create_message'))
            
            # 创建消息
            message = Message(
                sender_id=current_user.id,
                receiver_id=receiver_id,
                subject=subject,
                content=content
            )
            
            db.session.add(message)
            db.session.commit()
            
            log_action('send_message', f'发送消息给 {receiver.username}: {subject}')
            flash('消息发送成功', 'success')
            return redirect(url_for('admin.messages'))
        
        # 获取所有学生用户
        students = User.query.join(Role).filter(Role.name == 'Student').all()
        
        return render_template('admin/message_form.html', 
                              students=students,
                              title='发送消息',
                              form=form)
    except Exception as e:
        logger.error(f"Error in create_message: {e}")
        flash('发送消息时出错', 'danger')
        return redirect(url_for('admin.messages'))

@admin_bp.route('/message/<int:id>')
@admin_required
def view_message(id):
    try:
        # 查询消息
        message = db.get_or_404(Message, id)
        
        # 预加载发送者和接收者信息，避免在模板中引发懒加载
        sender = db.session.get(User, message.sender_id) if message.sender_id else None
        receiver = db.session.get(User, message.receiver_id) if message.receiver_id else None
        
        sender_info = None
        receiver_info = None
        
        if sender:
            sender_info = db.session.execute(db.select(StudentInfo).filter_by(user_id=sender.id)).scalar_one_or_none()
        
        if receiver:
            receiver_info = db.session.execute(db.select(StudentInfo).filter_by(user_id=receiver.id)).scalar_one_or_none()
        
        # 如果当前管理员是接收者且消息未读，则标记为已读
        if message.receiver_id == current_user.id and not message.is_read:
            message.is_read = True
            db.session.commit()
            
        # 导入display_datetime
        from src.utils.time_helpers import display_datetime
            
        return render_template('admin/message_view.html',
                             message=message,
                             sender=sender,
                             receiver=receiver,
                             sender_info=sender_info,
                             receiver_info=receiver_info,
                             display_datetime=display_datetime)
    except Exception as e:
        logger.error(f"Error in view_message: {e}")
        flash('查看消息时出错', 'danger')
        return redirect(url_for('admin.messages'))

@admin_bp.route('/message/<int:id>/delete', methods=['POST'])
@admin_required
def delete_message(id):
    try:
        message = db.get_or_404(Message, id)
        
        # 验证当前用户是否是消息的发送者或接收者
        if message.sender_id != current_user.id and message.receiver_id != current_user.id:
            flash('您无权删除此消息', 'danger')
            return redirect(url_for('admin.messages'))
        
        # 删除消息
        db.session.delete(message)
        db.session.commit()
        
        log_action('delete_message', f'删除消息: {message.subject}')
        flash('消息已删除', 'success')
        return redirect(url_for('admin.messages'))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in delete_message: {e}")
        flash('删除消息时出错', 'danger')
        return redirect(url_for('admin.messages'))

@admin_bp.route('/system/fix_timezone', methods=['GET', 'POST'])
@admin_required
def fix_timezone():
    try:
        messages = []
        
        if request.method == 'POST':
            if 'confirm' in request.form:
                # 检查要修复的项目
                fix_activities = 'fix_activities' in request.form
                fix_posters = 'fix_posters' in request.form
                fix_notifications = 'fix_notifications' in request.form
                fix_other_dates = 'fix_other_dates' in request.form
                
                # 设置环境变量，标记为Render环境
                os.environ['RENDER'] = 'true'
                
                # 获取数据库连接
                conn = None
                cursor = None
                try:
                    # 使用应用配置的数据库URI
                    db_uri = current_app.config['SQLALCHEMY_DATABASE_URI']
                    
                    # 如果是PostgreSQL数据库
                    if db_uri.startswith('postgresql'):
                        import psycopg2
                        conn = psycopg2.connect(db_uri)
                        cursor = conn.cursor()
                        
                        # 设置数据库时区为UTC
                        cursor.execute("SET timezone TO 'UTC';")
                        messages.append("数据库时区已设置为UTC")
                        
                        # 修复活动表中的时间字段
                        if fix_activities:
                            logger.info("修复活动表中的时间字段...")
                            
                            # 1. 修复活动开始时间
                            cursor.execute("""
                            UPDATE activities
                            SET start_time = start_time AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
                            WHERE start_time IS NOT NULL;
                            """)
                            
                            # 2. 修复活动结束时间
                            cursor.execute("""
                            UPDATE activities
                            SET end_time = end_time AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
                            WHERE end_time IS NOT NULL;
                            """)
                            
                            # 3. 修复活动报名截止时间
                            cursor.execute("""
                            UPDATE activities
                            SET registration_deadline = registration_deadline AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
                            WHERE registration_deadline IS NOT NULL;
                            """)
                            
                            messages.append("活动时间字段已修复")
                        
                        # 修复海报路径问题
                        if fix_posters:
                            logger.info("修复活动海报路径问题...")
                            
                            # 获取所有活动的海报信息
                            cursor.execute("""
                            SELECT id, poster_image FROM activities
                            WHERE poster_image IS NOT NULL;
                            """)
                            activities_with_posters = cursor.fetchall()
                            
                            fixed_posters = 0
                            for activity_id, poster_path in activities_with_posters:
                                # 检查海报文件是否存在
                                if poster_path and 'None' in poster_path:
                                    # 修正海报路径：替换None为activity_id
                                    new_path = poster_path.replace('None', str(activity_id))
                                    
                                    # 更新数据库中的路径
                                    cursor.execute("""
                                    UPDATE activities
                                    SET poster_image = %s
                                    WHERE id = %s;
                                    """, (new_path, activity_id))
                                    
                                    fixed_posters += 1
                            
                            if fixed_posters > 0:
                                messages.append(f"已修复 {fixed_posters} 个活动海报路径")
                            else:
                                messages.append("未发现需要修复的海报路径")
                        
                        # 修复通知表中的时间字段
                        if fix_notifications:
                            logger.info("修复通知表中的时间字段...")
                            
                            # 1. 修复通知创建时间
                            cursor.execute("""
                            UPDATE notification
                            SET created_at = created_at AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
                            WHERE created_at IS NOT NULL;
                            """)
                            
                            # 2. 修复通知过期时间
                            cursor.execute("""
                            UPDATE notification
                            SET expiry_date = expiry_date AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
                            WHERE expiry_date IS NOT NULL;
                            """)
                            
                            # 修复通知已读表中的时间字段
                            cursor.execute("""
                            UPDATE notification_read
                            SET read_at = read_at AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
                            WHERE read_at IS NOT NULL;
                            """)
                            
                            messages.append("通知时间字段已修复")
                        
                        # 修复其他日期时间字段
                        if fix_other_dates:
                            logger.info("修复其他日期时间字段...")
                            
                            # 修复站内信表中的时间字段
                            cursor.execute("""
                            UPDATE message
                            SET created_at = created_at AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
                            WHERE created_at IS NOT NULL;
                            """)
                            
                            # 修复报名表中的时间字段
                            logger.info("修复报名表中的时间字段...")
                            
                            # 1. 修复报名时间
                            cursor.execute("""
                            UPDATE registrations
                            SET register_time = register_time AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
                            WHERE register_time IS NOT NULL;
                            """)
                            
                            # 2. 修复签到时间
                            cursor.execute("""
                            UPDATE registrations
                            SET check_in_time = check_in_time AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
                            WHERE check_in_time IS NOT NULL;
                            """)
                            
                            # 修复系统日志表中的时间字段
                            cursor.execute("""
                            UPDATE system_logs
                            SET created_at = created_at AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
                            WHERE created_at IS NOT NULL;
                            """)
                            
                            # 修复积分历史表中的时间字段
                            cursor.execute("""
                            UPDATE points_history
                            SET created_at = created_at AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
                            WHERE created_at IS NOT NULL;
                            """)
                            
                            # 修复活动评价表中的时间字段
                            cursor.execute("""
                            UPDATE activity_reviews
                            SET created_at = created_at AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
                            WHERE created_at IS NOT NULL;
                            """)
                            
                            messages.append("其他日期时间字段已修复")
                        
                        # 提交所有更改
                        conn.commit()
                        
                        # 记录日志
                        log_action('fix_timezone', '修复数据库时区问题')
                        messages.append("所有修复操作已完成")
                    else:
                        messages.append("当前数据库不是PostgreSQL，无需修复时区问题。")
                
                except Exception as e:
                    if conn:
                        conn.rollback()
                    logger.error(f"时区修复失败: {e}")
                    messages.append(f"修复失败: {str(e)}")
                finally:
                    if cursor:
                        cursor.close()
                    if conn:
                        conn.close()
        
        return render_template('admin/fix_timezone.html', messages=messages)
    except Exception as e:
        logger.error(f"Error in fix_timezone: {e}")
        flash('访问时区修复页面时出错', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/activity/<int:id>/change_status', methods=['POST'])
@admin_required
def change_activity_status(id):
    try:
        activity = db.get_or_404(Activity, id)
        new_status = request.form.get('status')
        
        if new_status not in ['draft', 'pending', 'approved', 'active', 'completed', 'cancelled']:
            return jsonify({'success': False, 'message': '无效的状态'}), 400
        
        old_status = activity.status
        activity.status = new_status
        
        # 如果状态变为已完成，记录完成时间
        if new_status == 'completed' and not activity.completed_at:
            activity.completed_at = datetime.now(pytz.utc)
            
        db.session.commit()
        
        # 获取状态的中文名称
        status_names = {
            'draft': '草稿',
            'pending': '待审核',
            'approved': '已批准',
            'active': '进行中',
            'completed': '已完成',
            'cancelled': '已取消'
        }
        
        old_status_name = status_names.get(old_status, old_status)
        new_status_name = status_names.get(new_status, new_status)
        
        log_action('change_activity_status', f'更改活动状态: {activity.title}, 从 {old_status_name} 到 {new_status_name}')
        return jsonify({
            'success': True, 
            'message': f'活动状态已从"{old_status_name}"更新为"{new_status_name}"',
            'old_status': old_status,
            'new_status': new_status
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"更改活动状态出错: {e}")
        return jsonify({'success': False, 'message': '更改活动状态时出错'}), 500

@admin_bp.route('/activity/<int:activity_id>/manual_checkin', methods=['POST'])
@admin_required
def manual_checkin(activity_id):
    try:
        registration_id = request.form.get('registration_id')
        registration = db.get_or_404(Registration, registration_id)
        
        # 确保登记与活动匹配
        if registration.activity_id != activity_id:
            return jsonify({'success': False, 'message': '登记记录与活动不匹配'}), 400
        
        # 获取活动和学生信息
        activity = db.session.get(Activity, activity_id)
        student_info = StudentInfo.query.join(User).filter(User.id == registration.user_id).first()
        
        # 检查是否之前已经签到过（可能是被取消的签到）
        was_previously_checked_in = False
        
        # 查询积分历史记录，检查是否有取消参与的记录
        if student_info and activity:
            points = activity.points or (20 if activity.is_featured else 10)
            
            # 查找是否有取消参与该活动的积分记录
            cancel_record = PointsHistory.query.filter(
                PointsHistory.student_id == student_info.id,
                PointsHistory.activity_id == activity_id,
                PointsHistory.points == -points,
                PointsHistory.reason.like(f"取消参与活动：{activity.title}")
            ).first()
            
            was_previously_checked_in = cancel_record is not None
        
        # 设置签到时间
        registration.check_in_time = get_beijing_time()
        
        # 更新状态为已参加
        registration.status = 'attended'
        
        # 添加积分
        if student_info and activity:
            points = activity.points or (20 if activity.is_featured else 10)
            
            # 如果之前取消过签到并扣除了积分，则需要加回积分
            if was_previously_checked_in:
                add_points(student_info.id, points, f"重新参与活动：{activity.title}", activity.id)
            # 如果是首次签到，也添加积分
            elif registration.status != 'attended':
                add_points(student_info.id, points, f"参与活动：{activity.title}", activity.id)
        
        db.session.commit()
        
        log_action('manual_checkin', f'管理员手动签到: 活动={activity.title}, 学生={student_info.real_name if student_info else "未知"}')
        return jsonify({'success': True, 'message': '签到成功'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"手动签到出错: {e}")
        return jsonify({'success': False, 'message': '签到失败'}), 500

@admin_bp.route('/activity/<int:activity_id>/cancel_checkin', methods=['POST'])
@admin_required
def cancel_checkin(activity_id):
    try:
        registration_id = request.form.get('registration_id')
        registration = db.get_or_404(Registration, registration_id)
        
        # 确保登记与活动匹配
        if registration.activity_id != activity_id:
            return jsonify({'success': False, 'message': '登记记录与活动不匹配'}), 400
        
        # 判断原来是否已签到
        was_checked_in = registration.check_in_time is not None
        
        # 清除签到时间
        registration.check_in_time = None
        
        # 如果状态是已参与，改回已报名
        if registration.status == 'attended':
            registration.status = 'registered'
            
            # 扣除积分
            activity = db.session.get(Activity, activity_id)
            student_info = StudentInfo.query.join(User).filter(User.id == registration.user_id).first()
            
            if student_info and activity and was_checked_in:
                points = activity.points or (20 if activity.is_featured else 10)
                add_points(student_info.id, -points, f"取消参与活动：{activity.title}", activity.id)
        
        db.session.commit()
        
        log_action('cancel_checkin', f'取消签到: 活动ID={activity_id}, 登记ID={registration_id}')
        return jsonify({'success': True, 'message': '已取消签到'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"取消签到出错: {e}")
        return jsonify({'success': False, 'message': '取消签到失败'}), 500

# 添加积分辅助函数
def add_points(student_id, points, reason, activity_id=None):
    """为学生添加或扣除积分
    
    Args:
        student_id: 学生信息ID
        points: 积分变化，正数为增加，负数为减少
        reason: 积分变化原因
        activity_id: 相关活动ID，可选
        
    Returns:
        bool: 操作是否成功
    """
    try:
        # 获取学生信息
        student_info = db.session.get(StudentInfo, student_id)
        if not student_info:
            logger.error(f"添加积分失败: 学生ID {student_id} 不存在")
            return False
        
        # 更新积分
        student_info.points = (student_info.points or 0) + points
        
        # 创建积分历史记录
        points_history = PointsHistory(
            student_id=student_id,
            points=points,
            reason=reason,
            activity_id=activity_id
        )
        
        db.session.add(points_history)
        db.session.commit()
        
        logger.info(f"积分更新成功: 学生ID {student_id}, 变化 {points}, 原因: {reason}")
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"添加积分失败: {e}")
        return False

# 添加时间本地化辅助函数
def localize_time(dt):
    """将UTC时间转换为北京时间
    
    Args:
        dt: 日期时间对象
        
    Returns:
        datetime: 北京时间
    """
    if dt is None:
        return None
    
    # 确保时间是UTC时区
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=pytz.UTC)
    
    # 转换为北京时间
    beijing_tz = pytz.timezone('Asia/Shanghai')
    return dt.astimezone(beijing_tz)

# 公告管理路由
@admin_bp.route('/announcements')
@admin_required
def announcements():
    try:
        page = request.args.get('page', 1, type=int)
        announcements = Announcement.query.order_by(Announcement.created_at.desc()).paginate(page=page, per_page=10)
        
        # 确保display_datetime函数在模板中可用
        return render_template('admin/announcements.html', 
                              announcements=announcements,
                              display_datetime=display_datetime)
    except Exception as e:
        logger.error(f"Error in announcements page: {e}")
        flash('加载公告列表时出错', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/announcement/create', methods=['GET', 'POST'])
@admin_required
def create_announcement():
    try:
        if request.method == 'POST':
            title = request.form.get('title')
            content = request.form.get('content')
            status = request.form.get('status', 'published')
            
            if not title or not content:
                flash('标题和内容不能为空', 'danger')
                return redirect(url_for('admin.create_announcement'))
            
            # 创建公告
            announcement = Announcement(
                title=title,
                content=content,
                status=status,
                created_by=current_user.id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            db.session.add(announcement)
            db.session.commit()
            
            log_action('create_announcement', f'创建公告: {title}')
            flash('公告创建成功', 'success')
            return redirect(url_for('admin.announcements'))
        
        return render_template('admin/announcement_form.html', title='创建公告')
    except Exception as e:
        logger.error(f"Error in create_announcement: {e}")
        flash('创建公告时出错', 'danger')
        return redirect(url_for('admin.announcements'))

@admin_bp.route('/announcement/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_announcement(id):
    try:
        announcement = db.get_or_404(Announcement, id)
        
        if request.method == 'POST':
            title = request.form.get('title')
            content = request.form.get('content')
            status = request.form.get('status', 'published')
            
            if not title or not content:
                flash('标题和内容不能为空', 'danger')
                return redirect(url_for('admin.edit_announcement', id=id))
            
            # 更新公告
            announcement.title = title
            announcement.content = content
            announcement.status = status
            announcement.updated_at = datetime.now()
            
            db.session.commit()
            
            log_action('edit_announcement', f'编辑公告: {title}')
            flash('公告更新成功', 'success')
            return redirect(url_for('admin.announcements'))
        
        return render_template('admin/announcement_form.html', 
                              announcement=announcement,
                              title='编辑公告')
    except Exception as e:
        logger.error(f"Error in edit_announcement: {e}")
        flash('编辑公告时出错', 'danger')
        return redirect(url_for('admin.announcements'))

@admin_bp.route('/announcement/<int:id>/delete', methods=['POST'])
@admin_required
def delete_announcement(id):
    try:
        announcement = db.get_or_404(Announcement, id)
        
        # 删除公告
        db.session.delete(announcement)
        db.session.commit()
        
        log_action('delete_announcement', f'删除公告: {announcement.title}')
        flash('公告已删除', 'success')
        return redirect(url_for('admin.announcements'))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in delete_announcement: {e}")
        flash('删除公告时出错', 'danger')
        return redirect(url_for('admin.announcements'))

@admin_bp.route('/activity/<int:id>/view')
@admin_required
def activity_view(id):
    try:
        # 获取活动详情
        activity = db.get_or_404(Activity, id)
        
        # 获取报名统计
        registrations_count = db.session.execute(
            db.select(func.count()).select_from(Registration).filter_by(activity_id=id)
        ).scalar()
        
        # 获取签到统计
        checkins_count = db.session.execute(
            db.select(func.count()).select_from(Registration).filter_by(
                activity_id=id, 
                status='attended'
            )
        ).scalar()
        
        # 获取报名学生列表
        registrations = Registration.query.filter_by(
            activity_id=id
        ).join(
            User, Registration.user_id == User.id
        ).join(
            StudentInfo, User.id == StudentInfo.user_id
        ).add_columns(
            Registration.id.label('id'),
            Registration.register_time.label('registration_time'),
            Registration.check_in_time,
            StudentInfo.real_name.label('student_name'),
            StudentInfo.student_id.label('student_id'),
            StudentInfo.college.label('college'),
            StudentInfo.major.label('major')
        ).all()
        
        # 导入display_datetime函数供模板使用
        from src.utils.time_helpers import display_datetime
        
        # 创建CSRF表单对象
        from flask_wtf import FlaskForm
        form = FlaskForm()
        
        return render_template('admin/activity_view.html',
                              activity=activity,
                              registrations_count=registrations_count,
                              checkins_count=checkins_count,
                              registrations=registrations,
                              display_datetime=display_datetime,
                              form=form)
    except Exception as e:
        logger.error(f"Error in activity_view: {e}")
        flash('查看活动详情时出错', 'danger')
        return redirect(url_for('admin.activities'))

@admin_bp.route('/activity/<int:id>/delete', methods=['POST'])
@admin_required
def delete_activity(id):
    try:
        # 获取活动
        activity = db.get_or_404(Activity, id)
        
        # 检查是否强制删除
        force_delete = request.args.get('force', 'false').lower() == 'true'
        
        if force_delete:
            # 永久删除活动
            # 首先删除相关的报名记录
            Registration.query.filter_by(activity_id=id).delete()
            
            # 删除活动
            db.session.delete(activity)
            db.session.commit()
            
            # 记录操作
            log_action('force_delete_activity', f'永久删除活动: {activity.title}')
            
            flash(f'活动"{activity.title}"已永久删除', 'success')
        else:
            # 软删除（标记为已取消）
            activity.status = 'cancelled'
            db.session.commit()
            
            # 记录操作
            log_action('cancel_activity', f'取消活动: {activity.title}')
            
            flash(f'活动"{activity.title}"已标记为已取消', 'success')
        
        return redirect(url_for('admin.activities'))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting activity: {e}")
        flash('删除活动时出错', 'danger')
        return redirect(url_for('admin.activities'))
