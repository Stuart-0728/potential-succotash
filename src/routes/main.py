from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from src.models import db, Activity, Registration, User
from datetime import datetime
import logging
from src.routes.utils import log_action

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    try:
        # 获取最新活动
        latest_activities = Activity.query.filter_by(status='active').order_by(Activity.created_at.desc()).limit(6).all()
        
        # 获取即将截止报名的活动
        deadline_soon = Activity.query.filter(
            Activity.status == 'active',
            Activity.registration_deadline >= datetime.now()
        ).order_by(Activity.registration_deadline).limit(3).all()
        
        # 获取热门活动（报名人数最多的）
        popular_activities = Activity.query.join(
            Registration, Activity.id == Registration.activity_id
        ).filter(
            Activity.status == 'active',
            Registration.status == 'registered'
        ).group_by(Activity.id).order_by(
            db.func.count(Registration.id).desc()
        ).limit(3).all()
        
        return render_template('main/index.html', 
                              latest_activities=latest_activities,
                              deadline_soon=deadline_soon,
                              popular_activities=popular_activities,
                              now=datetime.now())
    except Exception as e:
        logger.error(f"Error in index: {e}")
        flash('加载首页时发生错误', 'danger')
        return render_template('main/index.html', 
                              latest_activities=[],
                              deadline_soon=[],
                              popular_activities=[],
                              now=datetime.now())

@main_bp.route('/activities')
def activities():
    try:
        page = request.args.get('page', 1, type=int)
        status = request.args.get('status', 'active')
        
        # 基本查询
        query = Activity.query
        
        # 根据状态筛选
        if status == 'active':
            query = query.filter(
                Activity.status == 'active',
                Activity.registration_deadline >= datetime.now()
            )
        elif status == 'past':
            query = query.filter(
                (Activity.status == 'completed') | 
                (Activity.registration_deadline < datetime.now())
            )
        
        # 获取活动列表
        activities_list = query.order_by(Activity.created_at.desc()).paginate(page=page, per_page=9)
        
        # 获取用户已报名的活动ID列表（如果已登录）
        registered_activity_ids = []
        if current_user.is_authenticated:
            registered = db.session.query(Registration.activity_id).filter(
                Registration.user_id == current_user.id,
                Registration.status == 'registered'
            ).all()
            registered_activity_ids = [r[0] for r in registered]
        
        return render_template('main/activities.html', 
                              activities=activities_list, 
                              current_status=status,
                              registered_activity_ids=registered_activity_ids,
                              now=datetime.now())
    except Exception as e:
        logger.error(f"Error in activities: {e}")
        flash('加载活动列表时发生错误', 'danger')
        return redirect(url_for('main.index'))

@main_bp.route('/activity/<int:id>')
def activity_detail(id):
    """允许任何人查看活动详情，但只有学生可以报名"""
    try:
        # 检查活动是否存在
        activity = Activity.query.get_or_404(id)
        
        # 检查用户是否已报名（仅针对已登录用户）
        registration = None
        can_register = False
        is_admin = False
        is_student = False
        
        if current_user.is_authenticated:
            # 检查用户角色
            if current_user.role:
                is_admin = current_user.role.name == 'Admin'
                is_student = current_user.role.name == 'Student'
            
            # 如果是学生，检查报名状态
            if is_student:
                registration = Registration.query.filter_by(
                    user_id=current_user.id,
                    activity_id=activity.id
                ).first()
                
                # 检查是否可以报名
                can_register = (
                    activity.status == 'active' and
                    activity.registration_deadline >= datetime.now() and
                    (not registration or registration.status == 'cancelled')
                )
                
                # 检查是否已达到人数上限
                if can_register and activity.max_participants > 0:
                    current_participants = Registration.query.filter_by(
                        activity_id=activity.id,
                        status='registered'
                    ).count()
                    if current_participants >= activity.max_participants:
                        can_register = False
        
        # 获取报名人数
        registration_count = Registration.query.filter_by(
            activity_id=activity.id,
            status='registered'
        ).count()
        
        # 获取创建者信息
        creator = User.query.get(activity.created_by) if activity.created_by else None
        
        # 渲染公共活动详情页面，所有人都可以查看
        return render_template('main/activity_detail.html', 
                              activity=activity,
                              registration=registration,
                              can_register=can_register,
                              is_admin=is_admin,
                              is_student=is_student,
                              registration_count=registration_count,
                              creator=creator,
                              now=datetime.now())
    except Exception as e:
        logger.error(f"Error in activity_detail: {e}")
        flash('查看活动详情时发生错误', 'danger')
        return redirect(url_for('main.activities'))

@main_bp.route('/about')
def about():
    try:
        return render_template('main/about.html')
    except Exception as e:
        logger.error(f"Error in about: {e}")
        flash('加载关于页面时发生错误', 'danger')
        return redirect(url_for('main.index'))

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
    """搜索页面，用于处理从导航栏搜索表单提交的请求"""
    try:
        query = request.args.get('q', '')
        category = request.args.get('category', 'all')
        page = request.args.get('page', 1, type=int)
        per_page = 10
        
        # 如果搜索词为空，重定向到首页
        if not query or len(query.strip()) < 2:
            flash('请输入至少2个字符进行搜索', 'warning')
            return redirect(url_for('main.index'))
        
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
        
        return render_template('main/search.html', 
                              query=query,
                              category=category,
                              activities=paginated_activities,
                              now=datetime.now())
    except Exception as e:
        logger.error(f"Error in search: {e}")
        flash('搜索时发生错误', 'danger')
        return redirect(url_for('main.index'))
