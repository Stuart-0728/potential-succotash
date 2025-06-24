from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort, send_from_directory, g, session, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import logging
from sqlalchemy import func, desc, text, and_, or_
from sqlalchemy.orm import joinedload
import time
import traceback
import pytz
from flask_wtf import FlaskForm
import os

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """首页"""
    try:
        start_time = datetime.now()
        
        # 延迟导入，避免循环导入问题
        from src import db
        from src.models import Activity, Registration, User, Tag, Notification
        from src.utils.time_helpers import get_beijing_time, ensure_timezone_aware, get_localized_now, safe_less_than, safe_greater_than, safe_compare
        
        # 获取当前时间（北京时间）
        now = get_beijing_time()
        logger.info(f"当前北京时间: {now}")
        
        # 获取未来一周的活动
        one_week_later = now + timedelta(days=7)
        upcoming_stmt = db.select(Activity).filter(
            Activity.start_time > now,
            Activity.start_time <= one_week_later,
            Activity.status == 'active'
        ).order_by(Activity.start_time)
        
        upcoming_activities = db.session.execute(upcoming_stmt).scalars().all()
        
        # 获取热门活动（报名人数最多的5个活动）
        popular_activities = []
        
        # 获取特色活动
        featured_stmt = db.select(Activity).filter(
            Activity.status == 'active',
            Activity.start_time > now
        ).order_by(func.random()).limit(3)
        
        featured_activities = db.session.execute(featured_stmt).scalars().all()
        
        # 添加调试信息，检查活动和海报信息
        for i, activity in enumerate(featured_activities):
            logger.info(f"特色活动 {i+1}: ID={activity.id}, 标题={activity.title}, 海报={activity.poster_image}")
            if activity.poster_image:
                # 检查并修复可能包含"None"的海报路径
                if "None" in activity.poster_image:
                    # 从文件名中提取时间戳部分
                    try:
                        parts = activity.poster_image.split('_')
                        if len(parts) >= 3:
                            # 替换None为实际活动ID
                            fixed_name = f"activity_{activity.id}_{parts[2]}"
                            activity.poster_image = fixed_name
                            logger.info(f"  修复海报文件名: {activity.poster_image}")
                    except Exception as e:
                        logger.error(f"  修复海报文件名出错: {e}")
                        activity.poster_image = None
                
                # 检查文件是否存在
                if activity.poster_image and current_app.static_folder:
                    poster_path = os.path.join(current_app.static_folder, 'uploads', 'posters', activity.poster_image)
                    if os.path.exists(poster_path):
                        logger.info(f"  海报文件存在: {poster_path}")
                    else:
                        logger.warning(f"  海报文件不存在: {poster_path}")
                        # 如果海报文件不存在，将海报字段设为None，避免前端显示错误
                        activity.poster_image = None
        
        # 获取系统公告 - 修正查询逻辑，获取重要通知
        public_notifications_stmt = db.select(Notification).filter(
            Notification.is_important == True,
            Notification.is_public == True,
            or_(
                Notification.expiry_date.is_(None),
                Notification.expiry_date > now
            )
        ).order_by(Notification.created_at.desc()).limit(3)
        
        public_notifications = db.session.execute(public_notifications_stmt).scalars().all()
        
        end_time = datetime.now()
        logger.debug(f"首页加载耗时: {(end_time - start_time).total_seconds():.2f}秒")
        
        return render_template('main/index.html', 
                               upcoming_activities=upcoming_activities,
                               popular_activities=popular_activities,
                               featured_activities=featured_activities,
                               public_notifications=public_notifications)
    except Exception as e:
        logger.error(f"Error in index: {e}", exc_info=True)
        flash("加载首页时发生错误，请稍后再试", "danger")
        return render_template('main/index.html', 
                               upcoming_activities=[],
                               popular_activities=[],
                               featured_activities=[],
                               public_notifications=[])

@main_bp.route('/activities')
def activities():
    try:
        # 延迟导入，避免循环导入问题
        from src.models import Activity, Registration
        from src.utils.time_helpers import get_beijing_time, safe_less_than, safe_greater_than, safe_compare
        from src import db
        
        # 获取当前北京时间
        now = get_beijing_time()
        
        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        search_query = request.args.get('search', '')
        status = request.args.get('status', 'active')
        
        # 基本查询
        query = db.select(Activity)
        
        # 搜索功能
        if search_query:
            query = query.filter(
                or_(
                    Activity.title.ilike(f'%{search_query}%'),
                    Activity.description.ilike(f'%{search_query}%'),
                    Activity.location.ilike(f'%{search_query}%')
                )
            )
        
        # 根据状态筛选 - 不比较时间，只使用活动状态
        if status == 'active':
            query = query.filter(Activity.status == 'active')
        elif status == 'past':
            query = query.filter(Activity.status == 'completed')
        
        # 排序
        query = query.order_by(Activity.created_at.desc())
        
        # 分页
        activities_list = db.paginate(query, page=page, per_page=9)
        
        # 获取用户已报名的活动ID列表
        registered_activity_ids = []
        if current_user.is_authenticated:
            reg_stmt = db.select(Registration.activity_id).filter(
                Registration.user_id == current_user.id,
                Registration.status == 'registered'
            )
            registered = db.session.execute(reg_stmt).all()
            registered_activity_ids = [r[0] for r in registered]
        
        return render_template('main/search.html',
                               activities=activities_list,
                               search_query=search_query,
                               current_status=status,
                               registered_activity_ids=registered_activity_ids,
                               now=now,
                               safe_less_than=safe_less_than,
                               safe_greater_than=safe_greater_than,
                               safe_compare=safe_compare)
        
    except Exception as e:
        logger.error(f"Error in activities page: {e}")
        flash('加载活动列表时发生错误', 'danger')
        return render_template('main/search.html', 
                               activities=None,
                               search_query='',
                               current_status='active',
                               safe_less_than=lambda x, y: False,
                               safe_greater_than=lambda x, y: False,
                               safe_compare=lambda x, y, op: False)

@main_bp.route('/activity/<int:activity_id>')
def activity_detail(activity_id):
    """活动详情页"""
    try:
        # 延迟导入，避免循环导入问题
        from src import db
        from src.models import Activity, Registration, User, Tag
        from src.utils.time_helpers import get_beijing_time, display_datetime, get_localized_now, safe_less_than, safe_greater_than, safe_compare, ensure_timezone_aware
        # 导入FlaskForm创建CSRF令牌
        from flask_wtf import FlaskForm
        
        activity = db.get_or_404(Activity, activity_id)
        
        # 创建空表单对象用于CSRF保护
        form = FlaskForm()
        
        # 获取报名人数
        reg_stmt = db.select(func.count()).select_from(Registration).filter_by(activity_id=activity_id)
        registration_count = db.session.execute(reg_stmt).scalar()
        logger.info(f"活动ID={activity_id} 的报名人数: {registration_count}")
        
        # 检查当前用户是否已报名
        is_registered = False
        registration = None
        if current_user.is_authenticated:
            reg_stmt = db.select(Registration).filter_by(
                user_id=current_user.id,
                activity_id=activity_id
            )
            registration = db.session.execute(reg_stmt).scalar_one_or_none()
            is_registered = registration is not None
        
        # 获取当前时间（带时区的UTC时间）
        now = get_localized_now()
        logger.info(f"当前UTC时间: {now}, 活动截止时间: {activity.registration_deadline}, 活动开始时间: {activity.start_time}")
        
        # 判断是否可以报名 - 使用安全比较函数
        # 确保所有时间都有时区信息
        deadline_aware = ensure_timezone_aware(activity.registration_deadline)
        start_time_aware = ensure_timezone_aware(activity.start_time)
        
        can_register = (
            not is_registered and 
            activity.status == 'active' and
            safe_greater_than(deadline_aware, now) and
            (activity.max_participants == 0 or registration_count < activity.max_participants)
        )
        
        # 判断是否可以取消报名 - 使用安全比较函数
        can_cancel = (
            is_registered and
            safe_greater_than(start_time_aware, now)
        )
        
        # 判断当前用户是否为学生
        is_student = current_user.is_authenticated and current_user.is_student
        
        return render_template('main/activity_detail.html', 
                              activity=activity,
                              registration_count=registration_count,
                              is_registered=is_registered,
                              registration=registration,
                              can_register=can_register,
                              can_cancel=can_cancel,
                              is_student=is_student,
                              display_datetime=display_datetime,
                              form=form,
                              now=now,
                              safe_less_than=safe_less_than,
                              safe_greater_than=safe_greater_than,
                              safe_compare=safe_compare)
    except Exception as e:
        logger.error(f"Error in activity_detail: {str(e)}")
        flash('加载活动详情时发生错误，请稍后再试', 'danger')
        return redirect(url_for('main.index'))

@main_bp.route('/about')
def about():
    """关于页面"""
    return render_template('main/about.html')

@main_bp.route('/contact')
def contact():
    try:
        return render_template('main/contact.html')
    except Exception as e:
        logger.error(f"Error in contact: {e}")
        flash('加载联系页面时发生错误', 'danger')
        return redirect(url_for('main.index'))

@main_bp.route('/privacy')
def privacy():
    try:
        return render_template('main/privacy.html')
    except Exception as e:
        logger.error(f"Error in privacy: {e}")
        flash('加载隐私政策页面时发生错误', 'danger')
        return redirect(url_for('main.index'))

@main_bp.route('/terms')
def terms():
    try:
        return render_template('main/terms.html')
    except Exception as e:
        logger.error(f"Error in terms: {e}")
        flash('加载使用条款页面时发生错误', 'danger')
        return redirect(url_for('main.index'))

@main_bp.route('/search')
def search():
    try:
        from src import db
        from src.models import Activity, Tag
        
        query = request.args.get('q', '')
        if not query:
            return render_template('main/search.html', activities=[], query='')
        
        # 使用SQLAlchemy 2.0语法进行搜索
        search_stmt = db.select(Activity).filter(
            or_(
                Activity.title.ilike(f'%{query}%'),
                Activity.description.ilike(f'%{query}%'),
                Activity.location.ilike(f'%{query}%')
            )
        ).order_by(Activity.created_at.desc())
        
        activities = db.session.execute(search_stmt).scalars().all()
        
        return render_template('main/search.html', activities=activities, query=query)
    except Exception as e:
        logger.error(f"Error in search: {e}")
        flash('搜索时发生错误', 'danger')
        return render_template('main/search.html', activities=[], query='')

@main_bp.route('/uploads/<path:filename>')
def uploaded_file(filename):
    try:
        return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)
    except Exception as e:
        logger.error(f"Error accessing uploaded file {filename}: {e}")
        abort(404)
