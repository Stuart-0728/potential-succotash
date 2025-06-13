from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from src.models import db, Activity, Registration, User, StudentInfo
import logging
from datetime import datetime, timedelta
import pandas as pd
import io
from werkzeug.utils import secure_filename
import os

logger = logging.getLogger(__name__)

utils_bp = Blueprint('utils', __name__, url_prefix='/utils')

# 管理员权限装饰器
def admin_required(f):
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.role or current_user.role.name != 'Admin':
            flash('您没有权限访问此页面', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# 记录用户操作日志
def log_action(user_id, action_type, description):
    try:
        from src.models import ActionLog
        
        log = ActionLog(
            user_id=user_id,
            action_type=action_type,
            description=description,
            ip_address=request.remote_addr,
            timestamp=datetime.now()
        )
        
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        logger.error(f"记录操作日志失败: {e}")
        db.session.rollback()

# 统计API
@utils_bp.route('/api/statistics')
@login_required
@admin_required
def api_statistics():
    try:
        stat_type = request.args.get('type', '')
        
        if stat_type == 'registrations_by_date':
            # 获取过去30天的报名数据
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            # 准备日期范围
            date_range = []
            current_date = start_date
            while current_date <= end_date:
                date_range.append(current_date.strftime('%Y-%m-%d'))
                current_date += timedelta(days=1)
            
            # 查询每天的报名数量
            registrations_by_date = {}
            for date_str in date_range:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                next_date = date_obj + timedelta(days=1)
                
                count = Registration.query.filter(
                    Registration.register_time >= date_obj,
                    Registration.register_time < next_date
                ).count()
                
                registrations_by_date[date_str] = count
            
            # 格式化为图表数据
            return jsonify({
                'labels': list(registrations_by_date.keys()),
                'values': list(registrations_by_date.values())
            })
        
        elif stat_type == 'registrations_by_college':
            # 获取按学院分组的报名数据
            registrations_by_college = db.session.query(
                StudentInfo.college,
                db.func.count(Registration.id)
            ).join(
                User, StudentInfo.user_id == User.id
            ).join(
                Registration, User.id == Registration.user_id
            ).filter(
                Registration.status == 'registered'
            ).group_by(
                StudentInfo.college
            ).all()
            
            # 格式化为图表数据
            colleges = [r[0] if r[0] else '未知' for r in registrations_by_college]
            counts = [r[1] for r in registrations_by_college]
            
            return jsonify({
                'labels': colleges,
                'values': counts
            })
        
        elif stat_type == 'activities_by_status':
            # 获取按状态分组的活动数据
            active_count = Activity.query.filter_by(status='active').count()
            completed_count = Activity.query.filter_by(status='completed').count()
            cancelled_count = Activity.query.filter_by(status='cancelled').count()
            
            # 格式化为图表数据
            return jsonify({
                'labels': ['进行中', '已结束', '已取消'],
                'values': [active_count, completed_count, cancelled_count]
            })
        
        elif stat_type == 'students_by_grade':
            # 获取按年级分组的学生数据
            students_by_grade = db.session.query(
                StudentInfo.grade,
                db.func.count(StudentInfo.id)
            ).group_by(
                StudentInfo.grade
            ).all()
            
            # 格式化为图表数据
            grades = [r[0] if r[0] else '未知' for r in students_by_grade]
            counts = [r[1] for r in students_by_grade]
            
            return jsonify({
                'labels': grades,
                'values': counts
            })
        
        else:
            return jsonify({'error': '未知的统计类型'}), 400
    
    except Exception as e:
        logger.error(f"统计API错误: {e}")
        return jsonify({'error': '获取统计数据时发生错误'}), 500

# 搜索API - 优化搜索功能，防止内存溢出
@utils_bp.route('/api/search')
@login_required
def api_search():
    try:
        query = request.args.get('q', '')
        category = request.args.get('category', 'all')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # 限制每页最大结果数，防止内存溢出
        if per_page > 50:
            per_page = 50
        
        # 如果搜索词为空，返回空结果
        if not query or len(query.strip()) < 2:
            return jsonify({
                'activities': [],
                'total': 0,
                'page': page,
                'per_page': per_page,
                'total_pages': 0
            })
        
        # 构建查询
        activities_query = Activity.query
        
        # 根据类别过滤
        if category == 'title':
            activities_query = activities_query.filter(Activity.title.ilike(f'%{query}%'))
        elif category == 'location':
            activities_query = activities_query.filter(Activity.location.ilike(f'%{query}%'))
        elif category == 'description':
            activities_query = activities_query.filter(Activity.description.ilike(f'%{query}%'))
        else:  # 'all'
            activities_query = activities_query.filter(
                db.or_(
                    Activity.title.ilike(f'%{query}%'),
                    Activity.location.ilike(f'%{query}%'),
                    Activity.description.ilike(f'%{query}%')
                )
            )
        
        # 分页查询
        paginated_activities = activities_query.order_by(
            Activity.start_time.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        # 格式化结果
        activities = []
        for activity in paginated_activities.items:
            activities.append({
                'id': activity.id,
                'title': activity.title,
                'location': activity.location,
                'start_time': activity.start_time.strftime('%Y-%m-%d %H:%M'),
                'status': activity.status,
                'url': url_for('main.activity_detail', id=activity.id)
            })
        
        return jsonify({
            'activities': activities,
            'total': paginated_activities.total,
            'page': page,
            'per_page': per_page,
            'total_pages': paginated_activities.pages
        })
    
    except Exception as e:
        logger.error(f"搜索API错误: {e}")
        return jsonify({'error': '搜索时发生错误'}), 500
