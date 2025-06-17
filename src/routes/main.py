from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort
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
    try:
        query = request.args.get('q', '')
        status = request.args.get('status', 'all')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        sort_by = request.args.get('sort', 'relevance')
        
        if not query and not any([status != 'all', start_date, end_date]):
            return render_template('main/search.html', 
                                query=query, 
                                activities=[],
                                status=status,
                                start_date=start_date,
                                end_date=end_date,
                                sort_by=sort_by)
        
        # 构建基础查询
        activities_query = Activity.query
        
        # 关键词搜索
        if query:
            activities_query = activities_query.filter(
                db.or_(
                    Activity.title.ilike(f'%{query}%'),
                    Activity.description.ilike(f'%{query}%'),
                    Activity.location.ilike(f'%{query}%')
                )
            )
        
        # 状态筛选
        if status != 'all':
            activities_query = activities_query.filter(Activity.status == status)
        
        # 日期筛选
        if start_date:
            try:
                start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
                activities_query = activities_query.filter(Activity.start_time >= start_datetime)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
                activities_query = activities_query.filter(Activity.start_time <= end_datetime)
            except ValueError:
                pass
        
        # 排序
        if sort_by == 'date_asc':
            activities_query = activities_query.order_by(Activity.start_time.asc())
        elif sort_by == 'date_desc':
            activities_query = activities_query.order_by(Activity.start_time.desc())
        elif sort_by == 'popularity':
            activities_query = activities_query.outerjoin(
                Registration, Activity.id == Registration.activity_id
            ).group_by(Activity.id).order_by(
                db.func.count(Registration.id).desc()
            )
        else:  # relevance (default)
            if query:
                # 根据匹配程度排序（标题匹配优先级最高）
                activities_query = activities_query.order_by(
                    db.case([
                        (Activity.title.ilike(f'{query}%'), 1),
                        (Activity.title.ilike(f'%{query}%'), 2)
                    ], else_=3),
                    Activity.start_time.desc()
                )
            else:
                activities_query = activities_query.order_by(Activity.start_time.desc())
        
        # 执行查询
        activities = activities_query.all()
        
        # 记录搜索词
        if query and len(query.strip()) > 0:
            log_action('search', f'搜索活动: {query}')
        
        return render_template('main/search.html',
                             query=query,
                             activities=activities,
                             status=status,
                             start_date=start_date,
                             end_date=end_date,
                             sort_by=sort_by,
                             total=len(activities))
    except Exception as e:
        logger.error(f"Error in search: {e}")
        # 如果渲染500页面也出错，则返回简单的错误信息
        return "搜索功能暂时不可用", 500
