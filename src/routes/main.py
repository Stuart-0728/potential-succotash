from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort, send_from_directory, g, session, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import logging
from sqlalchemy import func, desc, text, and_, or_
from sqlalchemy.orm import joinedload
import time
import traceback
import pytz

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
        
        # 获取当前北京时间
        now = get_beijing_time()
        logger.info(f"当前北京时间: {now}")
        
        # 获取未来7天内的活动
        end_date = now + timedelta(days=7)
        
        # 查询未来7天内的活动，按开始时间升序排序
        upcoming_activities = Activity.query.filter(
            Activity.start_time > now,
            Activity.start_time <= end_date,
            Activity.status == 'active'
        ).order_by(Activity.start_time).all()
        
        # 获取即将开始的活动（24小时内）
        soon_activities = []
        for activity in upcoming_activities:
            # 检查活动是否已经结束
            if activity.end_time <= now:
                logger.info(f"活动[{activity.id}-{activity.title}] 结束时间: {activity.end_time} <= 当前时间: {now}, 不显示在即将开始列表")
                continue
                
            # 检查活动是否在24小时内开始
            time_diff = activity.start_time - now
            if time_diff.total_seconds() <= 24 * 3600:  # 24小时内
                soon_activities.append(activity)
        
        # 获取当前正在进行的活动
        current_activities = Activity.query.filter(
            Activity.start_time <= now,
            Activity.end_time > now,
            Activity.status == 'active'
        ).all()
        
        # 获取最新的5个活动
        latest_activities = Activity.query.filter(
            Activity.status == 'active'
        ).order_by(desc(Activity.created_at)).limit(5).all()
        
        # 获取热门活动（报名人数最多的5个未结束活动）
        popular_activities = db.session.query(
            Activity, func.count(Registration.id).label('reg_count')
        ).join(Registration).filter(
            Activity.status == 'active',
            Activity.end_time > now
        ).group_by(Activity).order_by(
            desc('reg_count')
        ).limit(5).all()
        
        # 将查询结果转换为活动列表
        popular_activities = [item[0] for item in popular_activities]
        
        # 获取最新公告
        notifications = Notification.query.filter(
            Notification.is_public == True,
            or_(
                Notification.expiry_date.is_(None),
                Notification.expiry_date > now
            )
        ).order_by(desc(Notification.created_at)).limit(5).all()
        
        end_time = datetime.now()
        logger.info(f"首页加载耗时: {(end_time - start_time).total_seconds():.2f} 秒")
        
        return render_template('main/index.html', 
                              upcoming_activities=upcoming_activities,
                              soon_activities=soon_activities,
                              current_activities=current_activities,
                              latest_activities=latest_activities,
                              popular_activities=popular_activities,
                              notifications=notifications,
                              now=now)
    except Exception as e:
        logger.error(f"Error in index: {str(e)}")
        logger.error(traceback.format_exc())
        flash('加载首页时发生错误，请稍后再试', 'danger')
        return render_template('main/index.html', 
                              upcoming_activities=[],
                              soon_activities=[],
                              current_activities=[],
                              latest_activities=[],
                              popular_activities=[],
                              notifications=[])

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
        query = Activity.query
        
        # 搜索功能
        if search_query:
            query = query.filter(
                (Activity.title.ilike(f'%{search_query}%')) |
                (Activity.description.ilike(f'%{search_query}%')) |
                (Activity.location.ilike(f'%{search_query}%'))
            )
        
        # 根据状态筛选 - 不比较时间，只使用活动状态
        if status == 'active':
            query = query.filter(Activity.status == 'active')
        elif status == 'past':
            query = query.filter(Activity.status == 'completed')
        
        # 分页
        activities_list = query.order_by(Activity.created_at.desc()).paginate(
            page=page, per_page=9, error_out=False
        )
        
        # 获取用户已报名的活动ID列表
        registered_activity_ids = []
        if current_user.is_authenticated:
            registered = db.session.query(Registration.activity_id).filter(
                Registration.user_id == current_user.id,
                Registration.status == 'registered'
            ).all()
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
                               safe_less_than=safe_less_than,
                               safe_greater_than=safe_greater_than,
                               safe_compare=safe_compare)

@main_bp.route('/activity/<int:activity_id>')
def activity_detail(activity_id):
    """活动详情页"""
    try:
        # 延迟导入，避免循环导入问题
        from src import db
        from src.models import Activity, Registration, User, Tag
        from src.utils.time_helpers import get_beijing_time
        
        activity = Activity.query.get_or_404(activity_id)
        
        # 获取报名人数
        registration_count = Registration.query.filter_by(activity_id=activity_id).count()
        logger.info(f"活动ID={activity_id} 的报名人数: {registration_count}")
        
        # 检查当前用户是否已报名
        is_registered = False
        if current_user.is_authenticated:
            registration = Registration.query.filter_by(
                user_id=current_user.id,
                activity_id=activity_id
            ).first()
            is_registered = registration is not None
        
        # 获取当前北京时间
        now = get_beijing_time()
        
        # 判断是否可以报名
        can_register = (
            not is_registered and 
            activity.status == 'active' and
            activity.registration_deadline > now and
            (activity.max_participants == 0 or registration_count < activity.max_participants)
        )
        
        # 判断是否可以取消报名
        can_cancel = (
            is_registered and
            activity.start_time > now
        )
        
        return render_template('main/activity_detail.html', 
                              activity=activity,
                              registration_count=registration_count,
                              is_registered=is_registered,
                              can_register=can_register,
                              can_cancel=can_cancel,
                              now=now)
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
    """搜索页面"""
    query = request.args.get('q', '')
    if not query:
        return render_template('main/search.html', results=[], query='')
    
    try:
        # 延迟导入，避免循环导入问题
        from src import db
        from src.models import Activity
        from src.utils.time_helpers import get_beijing_time
        
        # 搜索活动标题和描述
        results = Activity.query.filter(
            Activity.status == 'active',
            or_(
                Activity.title.ilike(f'%{query}%'),
                Activity.description.ilike(f'%{query}%'),
                Activity.location.ilike(f'%{query}%'),
                Activity.type.ilike(f'%{query}%')
            )
        ).all()
        
        return render_template('main/search.html', results=results, query=query)
    except Exception as e:
        logger.error(f"Error in search: {str(e)}")
        flash('搜索时发生错误，请稍后再试', 'danger')
        return render_template('main/search.html', results=[], query=query)

@main_bp.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """提供上传文件的访问"""
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)
