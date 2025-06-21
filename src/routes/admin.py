from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file, current_app, abort
from flask_login import login_required, current_user
from src.models import User, Activity, Registration, StudentInfo, db, Tag, ActivityReview, ActivityCheckin, Role, PointsHistory, SystemLog, activity_tags, student_tags
from src.routes.utils import admin_required, log_action, add_points
from datetime import datetime, timedelta
import pandas as pd
import io
import logging
import json
from sqlalchemy import func, desc, and_, or_, not_
from src.forms import ActivityForm, SearchForm
import os
import shutil
from werkzeug.utils import secure_filename
import qrcode
from io import BytesIO
import hashlib
from src.utils.time_helpers import get_localized_now, get_beijing_time, localize_time, is_render_environment, normalize_datetime_for_db, ensure_timezone_aware
import base64
import random
import string
from functools import wraps
import tempfile
import csv
import zipfile

admin_bp = Blueprint('admin', __name__)
logger = logging.getLogger(__name__)

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    try:
        # 获取基本统计数据
        total_students = db.session.query(StudentInfo).count()
        total_activities = Activity.query.count()
        active_activities = Activity.query.filter_by(status='active').count()
        
        # 获取最近活动
        recent_activities = Activity.query.order_by(Activity.created_at.desc()).limit(5).all()
        
        # 获取最近注册的学生 - 修复查询，使用Role关联而不是role_id
        recent_students = User.query.join(Role).filter(Role.name == 'Student').join(
            StudentInfo, User.id == StudentInfo.user_id
        ).order_by(User.created_at.desc()).limit(5).all()
        
        # 获取报名统计
        total_registrations = Registration.query.count()
        
        return render_template('admin/dashboard.html',
                              total_students=total_students,
                              total_activities=total_activities,
                              active_activities=active_activities,
                              recent_activities=recent_activities,
                              recent_students=recent_students,
                              total_registrations=total_registrations)
    except Exception as e:
        logger.error(f"Error in admin dashboard: {e}")
        flash('加载管理面板时出错', 'danger')
        return render_template('admin/dashboard.html')

@admin_bp.route('/activities')
@admin_bp.route('/activities/<status>')
@admin_required
def activities(status='all'):
    try:
        page = request.args.get('page', 1, type=int)
        
        query = Activity.query
        
        # 根据状态筛选
        if status == 'active':
            query = query.filter_by(status='active')
        elif status == 'completed':
            query = query.filter_by(status='completed')
        elif status == 'cancelled':
            query = query.filter_by(status='cancelled')
        
        # 分页查询
        activities = query.order_by(Activity.created_at.desc()).paginate(page=page, per_page=10)
        
        # 为每个活动提前统计报名人数，避免模板中重复查询
        registration_counts = {}
        for activity in activities.items:
            count = Registration.query.filter_by(activity_id=activity.id, status='registered').count()
            registration_counts[activity.id] = count
        
        return render_template('admin/activities.html', 
                              activities=activities, 
                              current_status=status,
                              registration_counts=registration_counts)
    except Exception as e:
        logger.error(f"Error in activities page: {e}")
        flash('加载活动列表时出错', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/activity/create', methods=['GET', 'POST'])
@admin_required
def create_activity():
    try:
        form = ActivityForm()
        
        # 加载所有标签并设置选项
        tags = Tag.query.order_by(Tag.name).all()
        choices = [(tag.id, tag.name) for tag in tags]
        form.tags.choices = choices
        
        # 确保form.tags.data初始化为空列表而不是None
        if form.tags.data is None:
            form.tags.data = []
        
        if form.validate_on_submit():
            # 创建新活动
            activity = Activity(
                title=form.title.data,
                description=form.description.data,
                location=form.location.data,
                start_time=normalize_datetime_for_db(form.start_time.data),
                end_time=normalize_datetime_for_db(form.end_time.data),
                registration_deadline=normalize_datetime_for_db(form.registration_deadline.data),
                max_participants=form.max_participants.data,
                type=form.type.data if hasattr(form, 'type') else '其他',
                status=form.status.data,
                is_featured=form.is_featured.data,
                points=form.points.data or (20 if form.is_featured.data else 10),
                created_by=current_user.id
            )
            
            # 处理标签
            tag_ids = request.form.getlist('tags')  # 直接从请求中获取多选框值
            for tag_id in tag_ids:
                tag = Tag.query.get(int(tag_id))
                if tag:
                    activity.tags.append(tag)
            
            # 保存到数据库
            db.session.add(activity)
            db.session.commit()
            
            # 记录日志
            log_action('create_activity', f'创建活动: {activity.title}')
            
            # 处理上传的图片
            if form.poster.data:
                poster_path = handle_poster_upload(form.poster.data, activity.id)
                if poster_path:
                    activity.poster_url = poster_path
                    db.session.commit()
            
            flash('活动创建成功', 'success')
            return redirect(url_for('admin.activities'))
        
        return render_template('admin/activity_form.html', form=form, title='创建新活动')
    
    except Exception as e:
        logger.error(f"加载创建活动页面时出错: {str(e)}")
        logger.error(f"错误类型: {type(e)}")
        logger.error(f"堆栈跟踪: ", exc_info=True)
        flash('加载创建活动页面时出错', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/activity/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_activity(id):
    try:
        activity = Activity.query.get_or_404(id)
        form = ActivityForm(obj=activity)
        
        # 加载所有标签并设置选项
        tags = Tag.query.order_by(Tag.name).all()
        form.tags.choices = [(tag.id, tag.name) for tag in tags]
        
        # 设置当前活动的已选标签
        if request.method == 'GET':
            form.tags.data = [tag.id for tag in activity.tags]
            # 设置is_featured和points字段的值
            form.is_featured.data = activity.is_featured
            form.points.data = activity.points or (20 if activity.is_featured else 10)
        
        if request.method == 'POST' and form.validate_on_submit():
            try:
                # 将表单数据复制到活动对象，但不包括标签
                for field in form:
                    if field.name != 'tags' and field.name != 'submit' and field.name != 'poster':
                        setattr(activity, field.name, field.data)
                
                # 确保points字段有值
                if not activity.points:
                    activity.points = 20 if activity.is_featured else 10
                
                # 处理标签
                activity.tags.clear()
                tag_ids = request.form.getlist('tags')  # 直接从请求中获取多选框值
                for tag_id in tag_ids:
                    tag = Tag.query.get(int(tag_id))
                    if tag:
                        activity.tags.append(tag)
                
                # 确保时间字段正确处理
                activity.start_time = normalize_datetime_for_db(activity.start_time)
                activity.end_time = normalize_datetime_for_db(activity.end_time)
                activity.registration_deadline = normalize_datetime_for_db(activity.registration_deadline)
                
                db.session.commit()
                
                log_action('edit_activity', f'编辑活动: {activity.title}')
                flash('活动更新成功', 'success')
                return redirect(url_for('admin.activities'))
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error updating activity: {e}")
                flash(f'更新活动时出错: {str(e)}', 'danger')
        
        return render_template('admin/activity_form.html', form=form, activity=activity)
    except Exception as e:
        logger.error(f"Error in edit_activity: {e}")
        flash('编辑活动时出错', 'danger')
        return redirect(url_for('admin.activities'))

@admin_bp.route('/activity/<int:id>/view')
@admin_required
def activity_view(id):
    try:
        activity = Activity.query.get_or_404(id)
        registrations = Registration.query.filter_by(
            activity_id=id
        ).join(
            User, Registration.user_id == User.id
        ).join(
            StudentInfo, User.id == StudentInfo.user_id
        ).add_columns(
            Registration.id.label('registration_id'),
            Registration.register_time,
            Registration.status,
            Registration.check_in_time,
            StudentInfo.real_name,
            StudentInfo.student_id,
            StudentInfo.grade,
            StudentInfo.college,
            StudentInfo.major
        ).all()
        
        registration_count = len(registrations)
        
        return render_template('admin/activity_view.html', 
                              activity=activity,
                              registrations=registrations,
                              registration_count=registration_count)
        
    except Exception as e:
        logger.error(f"Error in activity_view: {e}")
        flash('查看活动详情时出错', 'danger')
        return redirect(url_for('admin.activities'))

@admin_bp.route('/activity/<int:id>/delete', methods=['POST'])
@admin_required
def delete_activity(id):
    try:
        activity = Activity.query.get_or_404(id)
        force_delete = request.args.get('force', 'false').lower() == 'true'
        
        # 使用事务
        with db.session.begin_nested():
            if force_delete:
                # 强制删除活动及相关数据
                # 先删除积分历史记录
                PointsHistory.query.filter_by(activity_id=activity.id).delete()
                Registration.query.filter_by(activity_id=activity.id).delete()
                ActivityReview.query.filter_by(activity_id=activity.id).delete()
                ActivityCheckin.query.filter_by(activity_id=activity.id).delete()
                
                # 删除活动与标签的关联
                activity.tags = []
                
                # 删除活动
                db.session.delete(activity)
                log_action('delete_activity', f'永久删除活动: {activity.title}')
                flash('活动已永久删除', 'success')
            elif Registration.query.filter_by(activity_id=activity.id).count() == 0:
                # 如果没有报名记录，直接删除活动
                # 先删除积分历史记录
                PointsHistory.query.filter_by(activity_id=activity.id).delete()
                ActivityReview.query.filter_by(activity_id=activity.id).delete()
                ActivityCheckin.query.filter_by(activity_id=activity.id).delete()
                
                # 删除活动与标签的关联
                activity.tags = []
                
                # 删除活动
                db.session.delete(activity)
                log_action('delete_activity', f'删除活动: {activity.title}')
                flash('活动已删除', 'success')
            else:
                # 如果有报名记录且不是强制删除，则标记为已取消
                activity.status = 'cancelled'
                log_action('cancel_activity', f'取消活动: {activity.title}')
                flash('活动已标记为已取消', 'success')
        
        db.session.commit()
        
        return redirect(url_for('admin.activities'))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting activity: {e}")
        flash('删除活动时出错', 'danger')
        return redirect(url_for('admin.activities'))

@admin_bp.route('/students')
@admin_required
def students():
    try:
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '')
        
        query = StudentInfo.query.join(User, StudentInfo.user_id == User.id)
        
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
        
        students = query.order_by(StudentInfo.id.desc()).paginate(page=page, per_page=20)
        
        return render_template('admin/students.html', students=students, search=search)
    except Exception as e:
        logger.error(f"Error in students: {e}")
        flash('加载学生列表时出错', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/student/<int:id>/delete', methods=['POST'])
@admin_required
def delete_student(id):
    try:
        user = User.query.get_or_404(id)
        
        # 确保是学生账号
        if user.role_id != 2:
            flash('只能删除学生账号', 'danger')
            return redirect(url_for('admin.students'))
        
        # 删除关联的学生信息
        student_info = StudentInfo.query.filter_by(user_id=id).first()
        if student_info:
            db.session.delete(student_info)
        
        # 删除关联的报名记录
        registrations = Registration.query.filter_by(user_id=id).all()
        for reg in registrations:
            db.session.delete(reg)
        
        # 删除用户账号
        db.session.delete(user)
        db.session.commit()
        
        log_action('delete_student', f'删除学生账号: {user.username}')
        flash('学生账号已删除', 'success')
        return redirect(url_for('admin.students'))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting student: {e}")
        flash('删除学生账号时出错', 'danger')
        return redirect(url_for('admin.students'))

@admin_bp.route('/student/<int:id>')
@admin_required
def student_view(id):
    student = StudentInfo.query.get_or_404(id)
    user = User.query.get(student.user_id)
    points_history = PointsHistory.query.filter_by(student_id=student.id).order_by(PointsHistory.created_at.desc()).all()
    registrations = Registration.query.filter_by(user_id=user.id).all()
    
    # 处理注册信息，添加活动标题
    for reg in registrations:
        activity = Activity.query.get(reg.activity_id)
        if activity:
            reg.activity_title = activity.title
        else:
            reg.activity_title = "未知活动"
    
    # 获取学生的标签
    selected_tag_ids = [tag.id for tag in student.tags] if student.tags else []
    
    # 获取所有标签
    all_tags = Tag.query.all()
    
    return render_template('admin/student_view.html', student=student, user=user, 
                           points_history=points_history, registrations=registrations,
                           selected_tag_ids=selected_tag_ids, all_tags=all_tags)

@admin_bp.route('/student/<int:id>/update-tags', methods=['POST'])
@admin_required
def update_student_tags(id):
    student = StudentInfo.query.get_or_404(id)
    
    try:
        # 获取提交的标签ID
        tag_ids = request.form.getlist('tags')
        
        # 清除原有标签关联
        student.tags = []
        
        # 添加新的标签关联
        for tag_id in tag_ids:
            tag = Tag.query.get(int(tag_id))
            if tag:
                student.tags.append(tag)
        
        # 更新学生标签选择状态
        student.has_selected_tags = True if tag_ids else False
        db.session.commit()
        
        flash('学生标签更新成功！', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"更新学生标签时出错: {e}")
        flash('更新学生标签时出错', 'danger')
    
    return redirect(url_for('admin.student_view', id=id))

@admin_bp.route('/student/<int:id>/adjust_points', methods=['POST'])
@admin_required
def adjust_student_points(id):
    try:
        student_info = StudentInfo.query.get_or_404(id)
        points = request.form.get('points', type=int)
        reason = request.form.get('reason', '').strip()
        
        if not points:
            flash('请输入有效的积分值', 'warning')
            return redirect(url_for('admin.student_view', id=id))
        
        if not reason:
            flash('请输入积分调整原因', 'warning')
            return redirect(url_for('admin.student_view', id=id))
        
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
        
        return redirect(url_for('admin.student_view', id=id))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in adjust_student_points: {e}")
        flash('调整积分时出错', 'danger')
        return redirect(url_for('admin.student_view', id=id))

@admin_bp.route('/statistics')
@admin_required
def statistics():
    try:
        # 活动统计
        total_activities = Activity.query.count()
        active_activities = Activity.query.filter_by(status='active').count()
        completed_activities = Activity.query.filter_by(status='completed').count()
        cancelled_activities = Activity.query.filter_by(status='cancelled').count()
        
        # 报名统计
        total_registrations = Registration.query.count()
        active_registrations = Registration.query.filter_by(status='registered').count()
        cancelled_registrations = Registration.query.filter_by(status='cancelled').count()
        
        # 计算平均每活动报名人数
        if total_activities > 0:
            avg_registrations_per_activity = total_registrations / total_activities
        else:
            avg_registrations_per_activity = 0
        
        # 获取报名率最高的活动
        most_popular_activity = None
        if total_activities > 0:
            activities_with_reg_count = db.session.query(
                Activity,
                func.count(Registration.id).label('reg_count')
            ).outerjoin(
                Registration, and_(Registration.activity_id == Activity.id, Registration.status == 'registered')
            ).group_by(Activity.id).order_by(desc('reg_count')).first()
            
            if activities_with_reg_count:
                most_popular_activity = activities_with_reg_count[0]
        
        # 学生统计
        total_students = User.query.filter_by(role_id=2).count()
        
        # 计算近30天活跃学生数
        thirty_days_ago = normalize_datetime_for_db(datetime.now()) - timedelta(days=30)
        active_students = Registration.query.filter(
            Registration.register_time >= thirty_days_ago
        ).with_entities(Registration.user_id).distinct().count()
        
        # 计算平均每学生参与活动数
        if total_students > 0:
            avg_activities_per_student = db.session.query(
                func.count(Registration.id) / total_students
            ).filter(Registration.status == 'registered').scalar() or 0
        else:
            avg_activities_per_student = 0
        
        # 获取最活跃学院
        most_active_college = db.session.query(
            StudentInfo.college,
            func.count(Registration.id).label('reg_count')
        ).join(
            User, StudentInfo.user_id == User.id
        ).join(
            Registration, Registration.user_id == User.id
        ).filter(
            Registration.status == 'registered'
        ).group_by(
            StudentInfo.college
        ).order_by(
            desc('reg_count')
        ).first()
        
        most_active_college = most_active_college[0] if most_active_college else None
        
        # 获取近30天的报名趋势数据
        registration_trend = []
        for i in range(30, -1, -1):
            date = normalize_datetime_for_db(datetime.now()) - timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')
            
            count = Registration.query.filter(
                func.date(Registration.register_time) == date.date()
            ).count()
            
            registration_trend.append({
                'date': date_str,
                'count': count
            })
        
        # 将趋势数据转换为JSON
        registration_trend_json = json.dumps(registration_trend)
        
        # 获取学院分布数据
        college_distribution = db.session.query(
            StudentInfo.college,
            func.count(StudentInfo.id).label('student_count')
        ).group_by(
            StudentInfo.college
        ).all()
        
        college_data = {
            'labels': [item[0] for item in college_distribution],
            'data': [item[1] for item in college_distribution]
        }
        
        # 获取年级分布数据
        grade_distribution = db.session.query(
            StudentInfo.grade,
            func.count(StudentInfo.id).label('student_count')
        ).group_by(
            StudentInfo.grade
        ).all()
        
        grade_data = {
            'labels': [item[0] for item in grade_distribution],
            'data': [item[1] for item in grade_distribution]
        }
        
        return render_template('admin/statistics.html',
                              total_activities=total_activities,
                              active_activities=active_activities,
                              completed_activities=completed_activities,
                              cancelled_activities=cancelled_activities,
                              total_registrations=total_registrations,
                              active_registrations=active_registrations,
                              cancelled_registrations=cancelled_registrations,
                              avg_registrations_per_activity=avg_registrations_per_activity,
                              most_popular_activity=most_popular_activity,
                              total_students=total_students,
                              active_students=active_students,
                              avg_activities_per_student=avg_activities_per_student,
                              most_active_college=most_active_college,
                              registration_trend=registration_trend_json,
                              college_data=json.dumps(college_data),
                              grade_data=json.dumps(grade_data))
    except Exception as e:
        logger.error(f"Error in statistics: {e}")
        flash('加载统计数据时出错', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/api/statistics')
@admin_required
def api_statistics():
    try:
        # 活动状态统计
        active_count = Activity.query.filter_by(status='active').count()
        completed_count = Activity.query.filter_by(status='completed').count()
        cancelled_count = Activity.query.filter_by(status='cancelled').count()
        
        registration_stats = {
            'labels': ['进行中', '已结束', '已取消'],
            'data': [active_count, completed_count, cancelled_count]
        }
        
        # 学生参与度统计
        total_students = User.query.filter_by(role_id=2).count()
        active_students = Registration.query.with_entities(Registration.user_id).distinct().count()
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
            
            # 当月活动数
            month_activities = Activity.query.filter(
                Activity.created_at >= month_start,
                Activity.created_at < month_end
            ).count()
            activities_count.append(month_activities)
            
            # 当月报名数
            month_registrations = Registration.query.filter(
                Registration.register_time >= month_start,
                Registration.register_time < month_end
            ).count()
            registrations_count.append(month_registrations)
        
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
        activity = Activity.query.get_or_404(id)
        
        # 获取报名学生列表 - 修复报名详情查看问题
        registrations = Registration.query.filter_by(
            activity_id=id
        ).join(
            User, Registration.user_id == User.id
        ).join(
            StudentInfo, User.id == StudentInfo.user_id
        ).add_columns(
            Registration.id.label('registration_id'),
            Registration.register_time,
            Registration.status,
            StudentInfo.real_name,
            StudentInfo.student_id,
            StudentInfo.grade,
            StudentInfo.college,
            StudentInfo.major,
            StudentInfo.phone,
            StudentInfo.points,  # 新增积分
            Registration.check_in_time  # 新增签到时间
        ).all()
        
        # 统计报名状态
        registered_count = Registration.query.filter_by(activity_id=id, status='registered').count()
        cancelled_count = Registration.query.filter_by(activity_id=id, status='cancelled').count()
        attended_count = Registration.query.filter_by(activity_id=id, status='attended').count()
        
        # 修复签到状态统计 - 确保报名统计准确性
        # 这里处理签到后的状态计数，让前端能正确显示
        
        return render_template('admin/activity_registrations.html',
                              activity=activity,
                              registrations=registrations,
                              registered_count=registered_count,
                              cancelled_count=cancelled_count,
                              attended_count=attended_count)
    except Exception as e:
        logger.error(f"Error in activity_registrations: {e}")
        flash('查看报名情况时出错', 'danger')
        return redirect(url_for('admin.activities'))

@admin_bp.route('/activity/<int:id>/export_excel')
@admin_required
def export_activity_registrations(id):
    try:
        activity = Activity.query.get_or_404(id)
        
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
                } for user in User.query.all()
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
                } for info in StudentInfo.query.all()
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
                } for activity in Activity.query.all()
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
                } for reg in Registration.query.all()
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
        registration = Registration.query.get_or_404(id)
        new_status = request.form.get('status')
        old_status = registration.status
        
        if new_status not in ['registered', 'cancelled', 'attended']:
            flash('无效的状态值', 'danger')
            return redirect(url_for('admin.activity_registrations', id=registration.activity_id))
        
        # 处理积分变更
        activity = Activity.query.get(registration.activity_id)
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
        student = StudentInfo.query.filter_by(student_id=student_id).first()
        if not student:
            return jsonify({'success': False, 'message': '学生不存在'})
        
        # 查找活动
        activity = Activity.query.get_or_404(id)
        
        # 查找报名记录
        registration = Registration.query.filter_by(
            user_id=student.user_id,
            activity_id=id
        ).first()
        
        if not registration:
            return jsonify({'success': False, 'message': '该学生未报名此活动'})
        
        if registration.check_in_time:
            return jsonify({'success': False, 'message': '该学生已签到'})
        
        # 更新签到状态
        registration.status = 'attended'
        registration.check_in_time = get_localized_now()
        
        # 添加积分奖励
        points = activity.points or (20 if activity.is_featured else 10)  # 使用活动自定义积分或默认值
        student_info = StudentInfo.query.filter_by(user_id=student.user_id).first()
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
    tags = Tag.query.order_by(Tag.created_at.desc()).all()
    return render_template('admin/tags.html', tags=tags)

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
        if Tag.query.filter_by(name=name).first():
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
        tag = Tag.query.get_or_404(id)
        name = request.form.get('name', '').strip()
        color = request.form.get('color', 'primary')
        
        if not name:
            flash('标签名称不能为空', 'danger')
            return redirect(url_for('admin.manage_tags'))
        
        # 检查新名称是否与其他标签重复
        existing_tag = Tag.query.filter(Tag.name == name, Tag.id != id).first()
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
        tag = Tag.query.get_or_404(id)
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
@admin_required
def api_statistics_ext():
    try:
        # 标签热度
        from src.models import Tag, Activity
        tag_stats = db.session.query(
            Tag.name, func.count(Activity.id)
        ).outerjoin(Activity.tags).group_by(Tag.id).all()
        tag_heat = {
            'labels': [t[0] for t in tag_stats],
            'data': [t[1] for t in tag_stats]
        }
        # 积分分布
        from src.models import StudentInfo
        points_bins = [0, 10, 30, 50, 100, 200, 500, 1000]
        bin_labels = [f'{points_bins[i]}-{points_bins[i+1]-1}' for i in range(len(points_bins)-1)] + [f'{points_bins[-1]}+']
        bin_counts = [0] * len(bin_labels)  # 修正：使用bin_labels的长度
        
        for stu in StudentInfo.query.all():
            points = stu.points or 0  # 处理None值
            bin_found = False  # 确保每个学生只被计入一个区间
            
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
        return jsonify({'tag_heat': tag_heat, 'points_dist': points_dist})
    except Exception as e:
        logger.error(f"Error in api_statistics_ext: {e}")
        return jsonify({'error': '获取扩展统计数据失败'}), 500

@admin_bp.route('/activity/<int:id>/reviews')
@admin_required
def activity_reviews(id):
    from src.models import Activity, ActivityReview
    activity = Activity.query.get_or_404(id)
    reviews = ActivityReview.query.filter_by(activity_id=id).order_by(ActivityReview.created_at.desc()).all()
    if reviews:
        average_rating = sum(r.rating for r in reviews) / len(reviews)
    else:
        average_rating = 0
    return render_template('admin/activity_reviews.html', activity=activity, reviews=reviews, average_rating=average_rating)

@admin_bp.route('/api/qrcode/checkin/<int:id>')
@admin_required
def generate_checkin_qrcode(id):
    try:
        # 检查活动是否存在
        activity = Activity.query.get_or_404(id)
        
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

# 添加二维码签到跳转路由
@admin_bp.route('/checkin/modal/<int:id>')
@admin_required
def checkin_modal(id):
    activity = Activity.query.get_or_404(id)
    return render_template('admin/checkin_modal.html', activity=activity)

# 切换活动签到状态
@admin_bp.route('/activity/<int:id>/toggle-checkin', methods=['POST'])
@admin_required
def toggle_checkin(id):
    try:
        activity = Activity.query.get_or_404(id)
        
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
        if referrer and ('checkin/modal' in referrer):
            return redirect(url_for('admin.checkin_modal', id=id))
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
                } for user in User.query.all()
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
                } for info in StudentInfo.query.all()
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
                } for activity in Activity.query.all()
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
                } for reg in Registration.query.all()
            ]
        
        # 备份标签数据
        if reset_tags:
            backup_data['data']['tags'] = [
                {
                    'name': tag.name,
                    'description': tag.description,
                    'color': tag.color
                } for tag in Tag.query.all()
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
            
            # 删除所有用户相关数据
            StudentInfo.query.delete()
            User.query.delete()
            db.session.commit()
            
            # 重新创建角色
            admin_role = Role.query.filter_by(name='Admin').first()
            if not admin_role:
                admin_role = Role(name='Admin', description='管理员')
                db.session.add(admin_role)
            
            student_role = Role.query.filter_by(name='Student').first()
            if not student_role:
                student_role = Role(name='Student', description='学生')
                db.session.add(student_role)
            
            db.session.commit()
            
            # 重新创建管理员账号
            admin = User(
                username=admin_username,
                email=admin_email,
                password_hash=admin_password,
                role_id=admin_role.id
            )
            db.session.add(admin)
            db.session.commit()
            
            flash('用户数据已重置，管理员账号已保留', 'success')
        
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
