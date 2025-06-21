from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_required, current_user
from src.models import db, Activity, Registration, User, Tag
from datetime import datetime, timedelta
import logging
from src.routes.utils import log_action
from src.utils.time_helpers import get_beijing_time, ensure_timezone_aware, get_localized_now
from sqlalchemy import func, desc, text

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    now = datetime.now()
    try:
        # 获取特色活动（按创建时间最新）
        featured_activities = Activity.query.filter_by(
            is_featured=True,
            status='active'
        ).filter(
            Activity.end_time >= ensure_timezone_aware(now)
        ).order_by(Activity.created_at.desc()).limit(3).all()
        
        # 获取即将开始的活动（按开始时间最近）
        upcoming_activities = Activity.query.filter_by(
            status='active'
        ).filter(
            Activity.start_time >= ensure_timezone_aware(now)
        ).order_by(Activity.start_time).limit(3).all()
        
        # 获取热门活动（报名人数最多）
        popular_activities_subquery = db.session.query(
            Activity.id,
            func.count(Registration.id).label('reg_count')
        ).join(
            Registration, Activity.id == Registration.activity_id
        ).filter(
            Activity.status == 'active',
            Activity.end_time >= ensure_timezone_aware(now)
        ).group_by(
            Activity.id
        ).subquery()
        
        popular_activities = db.session.query(
            Activity, popular_activities_subquery.c.reg_count
        ).join(
            popular_activities_subquery,
            Activity.id == popular_activities_subquery.c.id
        ).order_by(
            desc(popular_activities_subquery.c.reg_count)
        ).limit(3).all()
        
        # 从查询结果中提取活动对象
        popular_activity_objects = [item[0] for item in popular_activities]
        
        return render_template('main/index.html',
                              featured_activities=featured_activities,
                              upcoming_activities=upcoming_activities,
                              popular_activities=popular_activity_objects,
                              now=now)
    except Exception as e:
        logger.error(f"Error in index: {e}")
        # 如果出错，返回空列表
        return render_template('main/index.html',
                              featured_activities=[],
                              upcoming_activities=[],
                              popular_activities=[],
                              now=now)

@main_bp.route('/activities')
def activities():
    try:
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
        
        # 根据状态筛选
        if status == 'active':
            query = query.filter(
                Activity.status == 'active',
                Activity.registration_deadline >= now
            )
        elif status == 'past':
            query = query.filter(
                (Activity.status == 'completed') |
                (Activity.registration_deadline < now)
            )
        
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
                               now=now)
        
    except Exception as e:
        logger.error(f"Error in activities page: {e}")
        flash('加载活动列表时发生错误', 'danger')
        return render_template('main/search.html', 
                               activities=None,
                               search_query='',
                               current_status='active')

@main_bp.route('/activity/<int:id>')
def activity_detail(id):
    """允许任何人查看活动详情，但只有学生可以报名"""
    now = datetime.now()
    try:
        # 检查活动是否存在
        activity = Activity.query.get_or_404(id)
        
        # 获取创建者信息
        creator = User.query.get(activity.created_by) if activity.created_by else None
        
        # 检查用户是否已报名
        registration = None
        can_register = False
        if current_user.is_authenticated and hasattr(current_user, 'role') and current_user.role:
            if current_user.role.name.lower() == 'student':
                registration = Registration.query.filter_by(
                    activity_id=id,
                    user_id=current_user.id
                ).first()
                
                # 判断是否可以报名：活动状态为active，当前时间在报名截止时间之前，且未报名或已取消报名
                can_register = (
                    activity.status == 'active' and
                    activity.registration_deadline >= ensure_timezone_aware(now) and
                    (not registration or registration.status == 'cancelled')
                )
        
        # 获取报名人数
        registration_count = Registration.query.filter_by(
            activity_id=id,
            status='registered'
        ).count()
        
        # 获取活动标签
        tags = activity.tags
        
        return render_template('main/activity_detail.html',
                               activity=activity,
                               registration=registration,
                               can_register=can_register,
                               tags=tags,
                               registration_count=registration_count,
                               creator=creator,
                               now=now)
    except Exception as e:
        logger.error(f"Error in activity_detail: {e}")
        flash('加载活动详情时出错', 'danger')
        return redirect(url_for('main.index'))

@main_bp.route('/about')
def about():
    now = datetime.now()
    try:
        return render_template('main/about.html', now=now)
    except Exception as e:
        logger.error(f"Error in about page: {e}")
        flash('加载关于页面时出错', 'danger')
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
    now = datetime.now()
    try:
        query = request.args.get('q', '')
        tag_id = request.args.get('tag', type=int)
        status = request.args.get('status', 'active')
        sort_by = request.args.get('sort', 'newest')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not query and not tag_id and not start_date and not end_date and status == 'active':
            return redirect(url_for('main.index'))
        
        # 基础查询
        activities_query = Activity.query
        
        # 根据关键词搜索
        if query:
            activities_query = activities_query.filter(
                text("title LIKE :query OR description LIKE :query")
            ).params(query=f"%{query}%")
        
        # 根据标签搜索
        if tag_id:
            activities_query = activities_query.join(Activity.tags).filter(Tag.id == tag_id)
        
        # 根据状态搜索
        if status != 'all':
            activities_query = activities_query.filter(Activity.status == status)
        
        # 根据日期搜索
        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
                activities_query = activities_query.filter(Activity.start_time >= start_date_obj)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
                end_date_obj = end_date_obj.replace(hour=23, minute=59, second=59)
                activities_query = activities_query.filter(Activity.end_time <= end_date_obj)
            except ValueError:
                pass
        
        # 排序
        if sort_by == 'newest':
            activities_query = activities_query.order_by(Activity.created_at.desc())
        elif sort_by == 'start_time':
            activities_query = activities_query.order_by(Activity.start_time)
        elif sort_by == 'popular':
            # 这里需要一个子查询来获取报名人数
            subquery = db.session.query(
                Registration.activity_id, 
                func.count(Registration.id).label('reg_count')
            ).group_by(Registration.activity_id).subquery()
            
            activities_query = activities_query.outerjoin(
                subquery, Activity.id == subquery.c.activity_id
            ).order_by(
                desc(subquery.c.reg_count.nullsfirst())
            )
        
        # 执行查询
        activities = activities_query.all()
        
        # 获取所有标签用于筛选
        tags = Tag.query.order_by(Tag.name).all()
        
        return render_template('main/search.html',
                              query=query,
                              activities=activities,
                              tags=tags,
                              selected_tag=tag_id,
                              status=status,
                              start_date=start_date,
                              end_date=end_date,
                              sort_by=sort_by,
                              total=len(activities),
                              now=now)
    except Exception as e:
        logger.error(f"Error in search: {e}")
        flash('搜索时出错', 'danger')
        return redirect(url_for('main.index'))
