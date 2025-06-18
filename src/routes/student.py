from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from src.models import db, Activity, Registration, User, StudentInfo, PointsHistory, ActivityReview
from datetime import datetime, timedelta
import logging
import json
from functools import wraps
from src.routes.utils import log_action, random_string
from sqlalchemy import func, desc, or_, and_, not_
from wtforms import StringField, TextAreaField, IntegerField, SelectField, SubmitField, RadioField, BooleanField, HiddenField
from wtforms.validators import DataRequired, Length, Optional, NumberRange, Email, Regexp
from flask_wtf import FlaskForm
from src.utils.time_helpers import get_localized_now

logger = logging.getLogger(__name__)

student_bp = Blueprint('student', __name__, url_prefix='/student')

# 检查是否为学生的装饰器
def student_required(func):
    @login_required
    def decorated_view(*args, **kwargs):
        try:
            if not current_user.role or current_user.role.name != 'Student':
                flash('您没有权限访问此页面', 'danger')
                return redirect(url_for('main.index'))
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in student_required: {e}")
            flash('发生错误，请稍后再试', 'danger')
            return redirect(url_for('main.index'))
    decorated_view.__name__ = func.__name__
    return decorated_view

@student_bp.route('/dashboard')
@student_required
def dashboard():
    try:
        student_info = StudentInfo.query.filter_by(user_id=current_user.id).first()
        if not student_info:
            flash('请先完善个人信息', 'warning')
            return redirect(url_for('student.edit_profile'))
        
        # 获取推荐活动
        recommended_activities = get_recommended_activities(current_user.id)
        
        # 获取已报名活动
        registered_activities = Activity.query.join(
            Registration, Activity.id == Registration.activity_id
        ).filter(
            Registration.user_id == current_user.id,
            Registration.status == 'registered'
        ).order_by(Activity.start_time.desc()).limit(5).all()
        
        # 获取活动统计
        total_activities = Registration.query.filter_by(user_id=current_user.id).count()
        ongoing_activities = Registration.query.join(
            Activity, Registration.activity_id == Activity.id
        ).filter(
            Registration.user_id == current_user.id,
            Activity.status == 'active'
        ).count()
        
        # 获取即将开始的活动
        upcoming_registrations = Registration.query.join(
            Activity, Registration.activity_id == Activity.id
        ).filter(
            Registration.user_id == current_user.id,
            Activity.start_time > datetime.now()
        ).count()
        
        return render_template('student/dashboard.html',
                             student_info=student_info,
                             registered_activities=registered_activities,
                             recommended_activities=recommended_activities,
                             upcoming_activities=recommended_activities,
                             total_activities=total_activities,
                             ongoing_activities=ongoing_activities,
                             now=datetime.now())
    except Exception as e:
        logger.error(f"Error in student dashboard: {e}")
        flash('加载面板时发生错误', 'danger')
        return redirect(url_for('main.index'))

@student_bp.route('/activities')
@student_required
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
        activities_list = query.order_by(Activity.created_at.desc()).paginate(page=page, per_page=10)
        
        # 获取用户已报名的活动ID列表
        registered_activity_ids = db.session.query(Registration.activity_id).filter(
            Registration.user_id == current_user.id,
            Registration.status == 'registered'
        ).all()
        registered_activity_ids = [r[0] for r in registered_activity_ids]
        
        return render_template('student/activities.html', 
                              activities=activities_list, 
                              current_status=status,
                              registered_activity_ids=registered_activity_ids,
                              now=datetime.now())
    except Exception as e:
        logger.error(f"Error in student activities: {e}")
        flash('加载活动列表时发生错误', 'danger')
        return redirect(url_for('student.dashboard'))

@student_bp.route('/activity/<int:id>')
@student_required
def activity_detail(id):
    try:
        activity = Activity.query.get_or_404(id)
        
        # 获取当前用户的报名信息
        current_user_registration = Registration.query.filter_by(
            activity_id=id,
            user_id=current_user.id
        ).first()
        
        # 获取当前用户的评价
        current_user_review = ActivityReview.query.filter_by(
            activity_id=id,
            user_id=current_user.id
        ).first()
        
        # 获取所有评价
        reviews = ActivityReview.query.filter_by(activity_id=id).order_by(ActivityReview.created_at.desc()).all()
        
        # 计算平均评分
        if reviews:
            average_rating = sum(review.rating for review in reviews) / len(reviews)
            avg_content_quality = sum(review.content_quality for review in reviews) / len(reviews)
            avg_organization = sum(review.organization for review in reviews) / len(reviews)
            avg_facility = sum(review.facility for review in reviews) / len(reviews)
        else:
            average_rating = avg_content_quality = avg_organization = avg_facility = 0
        
        # 获取创建者信息
        creator = User.query.get(activity.created_by)
        
        # 获取已报名人数
        registered_count = Registration.query.filter_by(activity_id=id, status='registered').count()
        
        # 检查是否可以报名
        now = datetime.now()
        can_register = (
            activity.status == 'active' and 
            activity.registration_deadline >= now and 
            (activity.max_participants == 0 or registered_count < activity.max_participants)
        )
        
        return render_template('student/activity_detail.html',
                             activity=activity,
                             current_user_registration=current_user_registration,
                             current_user_review=current_user_review,
                             creator=creator,
                             registered_count=registered_count,
                             reviews=reviews,
                             average_rating=average_rating,
                             avg_content_quality=avg_content_quality,
                             avg_organization=avg_organization,
                             avg_facility=avg_facility,
                             can_register=can_register,
                             now=now)
    except Exception as e:
        logger.error(f"Error in activity detail: {e}")
        flash('加载活动详情时发生错误', 'danger')
        return redirect(url_for('student.activities'))

@student_bp.route('/activity/<int:id>/register', methods=['POST'])
@student_required
def register_activity(id):
    try:
        activity = Activity.query.get_or_404(id)
        
        # 检查活动是否可报名
        if activity.status != 'active' or activity.registration_deadline < datetime.now():
            flash('该活动已结束报名', 'danger')
            return redirect(url_for('student.activity_detail', id=id))
        
        # 检查是否已报名
        existing_registration = Registration.query.filter_by(
            user_id=current_user.id,
            activity_id=activity.id
        ).first()
        
        if existing_registration and existing_registration.status == 'registered':
            flash('您已报名过该活动', 'warning')
            return redirect(url_for('student.activity_detail', id=id))
        elif existing_registration and existing_registration.status == 'cancelled':
            # 如果之前取消过报名，则重新激活
            existing_registration.status = 'registered'
            existing_registration.register_time = datetime.now()
            db.session.commit()
            flash('重新报名成功！', 'success')
            return redirect(url_for('student.activity_detail', id=id))
        
        # 检查是否已达到人数上限
        if activity.max_participants > 0:
            current_participants = Registration.query.filter_by(
                activity_id=activity.id,
                status='registered'
            ).count()
            if current_participants >= activity.max_participants:
                flash('该活动报名人数已达上限', 'danger')
                return redirect(url_for('student.activity_detail', id=id))
        
        # 创建报名记录
        registration = Registration(
            user_id=current_user.id,
            activity_id=activity.id,
            register_time=datetime.now(),
            status='registered'
        )
        
        db.session.add(registration)
        db.session.commit()
        
        flash('报名成功！', 'success')
        return redirect(url_for('student.activity_detail', id=id))
    except Exception as e:
        logger.error(f"Error in register activity: {e}")
        db.session.rollback()
        flash('报名过程中发生错误，请稍后再试', 'danger')
        return redirect(url_for('student.activity_detail', id=id))

@student_bp.route('/activity/<int:id>/cancel', methods=['POST'])
@student_required
def cancel_registration(id):
    try:
        registration = Registration.query.filter_by(
            user_id=current_user.id,
            activity_id=id
        ).first_or_404()
        
        # 检查活动是否已开始
        activity = Activity.query.get(id)
        if activity.start_time <= datetime.now():
            flash('活动已开始，无法取消报名', 'danger')
            return redirect(url_for('student.activity_detail', id=id))
        
        # 取消报名
        registration.status = 'cancelled'
        db.session.commit()
        
        flash('已成功取消报名', 'success')
        return redirect(url_for('student.activity_detail', id=id))
    except Exception as e:
        logger.error(f"Error in cancel registration: {e}")
        db.session.rollback()
        flash('取消报名过程中发生错误，请稍后再试', 'danger')
        return redirect(url_for('student.activity_detail', id=id))

@student_bp.route('/my_activities')
@student_required
def my_activities():
    try:
        page = request.args.get('page', 1, type=int)
        status = request.args.get('status', 'all')
        
        # 获取用户的所有报名记录
        registrations = Registration.query.filter_by(user_id=current_user.id)
        
        # 根据状态筛选
        if status == 'upcoming':
            # 获取即将开始的活动ID
            upcoming_activity_ids = db.session.query(Activity.id).filter(
                Activity.start_time > datetime.now(),
                Activity.status == 'active'
            ).all()
            upcoming_activity_ids = [a[0] for a in upcoming_activity_ids]
            
            # 筛选用户报名的即将开始的活动
            registrations = registrations.filter(
                Registration.status == 'registered',
                Registration.activity_id.in_(upcoming_activity_ids)
            )
        elif status == 'past':
            # 获取已结束的活动ID
            past_activity_ids = db.session.query(Activity.id).filter(
                Activity.end_time < datetime.now()
            ).all()
            past_activity_ids = [a[0] for a in past_activity_ids]
            
            # 筛选用户报名的已结束活动
            registrations = registrations.filter(
                Registration.status == 'registered',
                Registration.activity_id.in_(past_activity_ids)
            )
        elif status == 'cancelled':
            # 筛选用户取消的报名
            registrations = registrations.filter(Registration.status == 'cancelled')
        
        # 分页获取报名记录
        registrations_page = registrations.order_by(Registration.register_time.desc()).paginate(page=page, per_page=10)
        
        # 获取相关活动信息
        activities_dict = {}
        for reg in registrations_page.items:
            if reg.activity_id not in activities_dict:
                activities_dict[reg.activity_id] = Activity.query.get(reg.activity_id)
        
        return render_template('student/my_activities.html', 
                              registrations=registrations_page,
                              activities=activities_dict,
                              current_status=status,
                              now=datetime.now())
    except Exception as e:
        logger.error(f"Error in my activities: {e}")
        flash('加载我的活动时发生错误', 'danger')
        return redirect(url_for('student.dashboard'))

@student_bp.route('/profile')
@student_required
def profile():
    try:
        return render_template('student/profile.html')
    except Exception as e:
        logger.error(f"Error in profile: {e}")
        flash('加载个人资料时发生错误', 'danger')
        return redirect(url_for('student.dashboard'))

@student_bp.route('/profile/edit', methods=['GET', 'POST'])
@student_required
def edit_profile():
    try:
        from flask_wtf import FlaskForm
        from wtforms import StringField, SubmitField
        from wtforms.validators import DataRequired, Length, Regexp
        
        class ProfileForm(FlaskForm):
            real_name = StringField('姓名', validators=[DataRequired(message='姓名不能为空')])
            grade = StringField('年级', validators=[DataRequired(message='年级不能为空')])
            major = StringField('专业', validators=[DataRequired(message='专业不能为空')])
            college = StringField('学院', validators=[DataRequired(message='学院不能为空')])
            phone = StringField('手机号', validators=[
                DataRequired(message='手机号不能为空'),
                Regexp('^1[3-9]\d{9}$', message='请输入有效的手机号码')
            ])
            qq = StringField('QQ号', validators=[
                DataRequired(message='QQ号不能为空'),
                Regexp('^\d{5,12}$', message='请输入有效的QQ号码')
            ])
            submit = SubmitField('保存修改')
        
        form = ProfileForm()
        student_info = current_user.student_info
        
        if form.validate_on_submit():
            student_info.real_name = form.real_name.data
            student_info.grade = form.grade.data
            student_info.major = form.major.data
            student_info.college = form.college.data
            student_info.phone = form.phone.data
            student_info.qq = form.qq.data
            
            db.session.commit()
            flash('个人信息更新成功！', 'success')
            return redirect(url_for('student.profile'))
        
        # 预填表单
        if request.method == 'GET':
            form.real_name.data = student_info.real_name
            form.grade.data = student_info.grade
            form.major.data = student_info.major
            form.college.data = student_info.college
            form.phone.data = student_info.phone
            form.qq.data = student_info.qq
        
        return render_template('student/edit_profile.html', form=form)
    except Exception as e:
        logger.error(f"Error in edit profile: {e}")
        flash('编辑个人资料时发生错误', 'danger')
        return redirect(url_for('student.profile'))

@student_bp.route('/delete_account', methods=['POST'])
@student_required
def delete_account():
    try:
        # 验证用户确认
        confirm_username = request.form.get('confirm_username')
        if not confirm_username or confirm_username != current_user.username:
            flash('用户名输入不正确，账号注销失败', 'danger')
            return redirect(url_for('student.profile'))
        
        user_id = current_user.id
        
        # 删除关联的报名记录
        Registration.query.filter_by(user_id=user_id).delete()
        
        # 删除学生信息
        StudentInfo.query.filter_by(user_id=user_id).delete()
        
        # 记录用户信息用于日志
        username = current_user.username
        
        # 登出用户
        from flask_login import logout_user
        logout_user()
        
        # 删除用户
        user = User.query.get(user_id)
        db.session.delete(user)
        db.session.commit()
        
        logger.info(f"User self-deleted: {username} (ID: {user_id})")
        flash('您的账号已成功注销，所有个人信息已被删除', 'success')
        return redirect(url_for('main.index'))
    except Exception as e:
        logger.error(f"Error in account deletion: {e}")
        db.session.rollback()
        flash('账号注销过程中发生错误，请稍后再试', 'danger')
        return redirect(url_for('student.profile'))

@student_bp.route('/points')
@login_required
def points():
    try:
        student_info = StudentInfo.query.filter_by(user_id=current_user.id).first()
        if not student_info:
            flash('请先完善个人信息', 'warning')
            return redirect(url_for('student.edit_profile'))
        
        points_history = PointsHistory.query.filter_by(student_id=student_info.id)\
            .order_by(PointsHistory.created_at.desc()).all()
        
        return render_template('student/points.html', 
                             student_info=student_info,
                             points_history=points_history)
    except Exception as e:
        logger.error(f"Error in student points page: {e}")
        flash('加载积分信息时出错', 'danger')
        return redirect(url_for('student.dashboard'))

def add_points(student_id, points, reason, activity_id=None):
    """添加积分的工具函数"""
    try:
        student = StudentInfo.query.get(student_id)
        if student:
            student.points += points
            
            history = PointsHistory(
                student_id=student_id,
                points=points,
                reason=reason,
                activity_id=activity_id
            )
            
            db.session.add(history)
            db.session.commit()
            return True
    except Exception as e:
        logger.error(f"Error adding points: {e}")
        db.session.rollback()
        return False

@student_bp.route('/activity/<int:activity_id>/review', methods=['GET', 'POST'])
@login_required
def review_activity(activity_id):
    try:
        # 检查活动是否存在且已结束
        activity = Activity.query.get_or_404(activity_id)
        if activity.status != 'completed':
            flash('只能评价已结束的活动', 'warning')
            return redirect(url_for('student.activity_detail', id=activity_id))
        
        # 检查是否已参加活动
        registration = Registration.query.filter_by(
            activity_id=activity_id,
            user_id=current_user.id,
            status='checked_in'
        ).first()
        
        if not registration:
            flash('只有参加过活动的学生才能评价', 'warning')
            return redirect(url_for('student.activity_detail', id=activity_id))
        
        # 检查是否已评价过
        existing_review = ActivityReview.query.filter_by(
            activity_id=activity_id,
            user_id=current_user.id
        ).first()
        
        if existing_review:
            flash('你已经评价过这个活动了', 'info')
            return redirect(url_for('student.activity_detail', id=activity_id))
        
        return render_template('student/review.html', activity=activity)
    except Exception as e:
        logger.error(f"Error in review activity page: {e}")
        flash('加载评价页面时出错', 'danger')
        return redirect(url_for('student.my_activities'))

@student_bp.route('/activity/<int:activity_id>/submit-review', methods=['POST'])
@login_required
def submit_review(activity_id):
    try:
        # 验证表单数据
        rating = request.form.get('rating', type=int)
        content_quality = request.form.get('content_quality', type=int)
        organization = request.form.get('organization', type=int)
        facility = request.form.get('facility', type=int)
        review_text = request.form.get('review', '').strip()
        is_anonymous = 'anonymous' in request.form
        
        if not all([rating, review_text]) or not (1 <= rating <= 5):
            flash('请填写完整的评价信息', 'warning')
            return redirect(url_for('student.review_activity', activity_id=activity_id))
        
        # 创建评价记录
        review = ActivityReview(
            activity_id=activity_id,
            user_id=current_user.id,
            rating=rating,
            content_quality=content_quality,
            organization=organization,
            facility=facility,
            review=review_text,
            is_anonymous=is_anonymous
        )
        
        db.session.add(review)
        # 添加积分奖励
        student_info = StudentInfo.query.filter_by(user_id=current_user.id).first()
        if student_info:
            add_points(student_info.id, 5, "提交活动评价")
        
        db.session.commit()
        flash('评价提交成功！获得5积分奖励', 'success')
        log_action('submit_review', f'提交活动评价: {activity_id}')
        
        return redirect(url_for('student.activity_detail', id=activity_id))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error submitting review: {e}")
        flash('提交评价时出错', 'danger')
        return redirect(url_for('student.review_activity', activity_id=activity_id))

@student_bp.route('/points/rank')
@login_required
def points_rank():
    from src.models import StudentInfo
    top_students = StudentInfo.query.order_by(StudentInfo.points.desc()).limit(100).all()
    return render_template('student/points_rank.html', top_students=top_students)

def get_recommended_activities(user_id, limit=6):
    """基于用户的历史参与记录和兴趣推荐活动"""
    try:
        # 获取用户信息
        student_info = StudentInfo.query.filter_by(user_id=user_id).first()
        if not student_info:
            return Activity.query.filter_by(status='active').order_by(Activity.created_at.desc()).limit(limit).all()
        
        # 获取用户历史参与的活动
        participated_activities = Activity.query.join(
            Registration, Activity.id == Registration.activity_id
        ).filter(
            Registration.user_id == user_id
        ).all()
        
        # 如果用户没有参与过任何活动，返回最新活动
        if not participated_activities:
            return Activity.query.filter_by(status='active').order_by(Activity.created_at.desc()).limit(limit).all()
        
        # 获取用户评价过的活动
        reviewed_activities = Activity.query.join(
            ActivityReview, Activity.id == ActivityReview.activity_id
        ).filter(
            ActivityReview.user_id == user_id,
            ActivityReview.rating >= 4  # 只考虑用户评价较高的活动
        ).all()
        
        # 构建推荐查询
        recommended = Activity.query.filter(
            Activity.status == 'active',
            Activity.id.notin_([a.id for a in participated_activities])  # 排除已参加的活动
        )
        
        # 如果有高评分活动，优先推荐类似活动
        if reviewed_activities:
            # 这里可以根据活动标题、描述等进行相似度匹配
            # 这是一个简化的实现，实际中可以使用更复杂的相似度算法
            liked_keywords = set()
            for activity in reviewed_activities:
                liked_keywords.update(activity.title.split())
                liked_keywords.update(activity.description.split())
            
            recommended = recommended.filter(
                db.or_(
                    *[Activity.title.ilike(f'%{keyword}%') for keyword in liked_keywords],
                    *[Activity.description.ilike(f'%{keyword}%') for keyword in liked_keywords]
                )
            )
        
        # 根据用户所在学院和专业推荐
        recommended = recommended.order_by(
            # 优先推荐用户所在学院的活动
            db.case((Activity.college == student_info.college, 1), else_=2),
            # 其次考虑活动开始时间
            Activity.start_time.asc()
        )
        
        return recommended.limit(limit).all()
    except Exception as e:
        logger.error(f"Error in getting recommended activities: {e}")
        return []

@student_bp.route('/recommend')
@login_required
def recommend():
    from src.models import Activity, Tag, Registration, StudentInfo
    # 获取当前学生已报名/参加过的活动标签
    stu_info = StudentInfo.query.filter_by(user_id=current_user.id).first()
    joined_activities = Registration.query.filter_by(user_id=current_user.id).with_entities(Registration.activity_id).all()
    joined_ids = [a[0] for a in joined_activities]
    tag_ids = set()
    for act in Activity.query.filter(Activity.id.in_(joined_ids)).all():
        tag_ids.update([t.id for t in act.tags])
    # 推荐同标签的其他活动，排除已报名/参加过的
    if tag_ids:
        recommended = Activity.query.join(Activity.tags).filter(
            Tag.id.in_(tag_ids),
            ~Activity.id.in_(joined_ids),
            Activity.status=='active'
        ).distinct().all()
    else:
        recommended = Activity.query.filter_by(status='active').order_by(Activity.created_at.desc()).limit(10).all()
    return render_template('student/recommendation.html', recommended=recommended)

@student_bp.route('/api/attendance/checkin', methods=['POST'])
@student_required
def checkin():
    try:
        data = request.get_json()
        activity_id = data.get('activity_id')
        qr_data = data.get('qr_data')
        
        if not activity_id or not qr_data:
            return jsonify({
                'success': False,
                'message': '缺少必要参数'
            }), 400
        
        # 验证活动是否存在且正在进行
        activity = Activity.query.get_or_404(activity_id)
        if activity.status != 'active':
            return jsonify({
                'success': False,
                'message': '活动未在进行中'
            }), 400
        
        # 验证当前时间是否在活动时间范围内
        now = get_localized_now()
        
        # 添加灵活度：允许活动开始前30分钟和结束后30分钟的签到
        start_time_buffer = activity.start_time - timedelta(minutes=30)
        end_time_buffer = activity.end_time + timedelta(minutes=30)
        
        logger.info(f"API签到时间检查: 当前时间={now}, 活动开始时间={activity.start_time}, 活动结束时间={activity.end_time}")
        
        if now < start_time_buffer or now > end_time_buffer:
            return jsonify({
                'success': False,
                'message': '不在活动签到时间范围内'
            }), 400
        
        # 验证用户是否已报名
        registration = Registration.query.filter_by(
            user_id=current_user.id,
            activity_id=activity_id,
            status='registered'
        ).first()
        
        if not registration:
            return jsonify({
                'success': False,
                'message': '您尚未报名此活动'
            }), 400
        
        # 验证是否已签到
        if registration.check_in_time:
            return jsonify({
                'success': False,
                'message': '您已经签到过了'
            }), 400
        
        # 验证二维码数据
        try:
            qr_data_dict = json.loads(qr_data)
            if str(qr_data_dict.get('activity_id')) != str(activity_id):
                return jsonify({
                    'success': False,
                    'message': '无效的签到二维码'
                }), 400
        except:
            return jsonify({
                'success': False,
                'message': '无效的签到二维码'
            }), 400
        
        # 更新签到状态
        registration.check_in_time = now
        registration.status = 'checked_in'
        
        # 添加积分奖励
        points = activity.points or (20 if activity.is_featured else 10)  # 使用活动自定义积分或默认值
        student_info = StudentInfo.query.filter_by(user_id=current_user.id).first()
        if student_info:
            student_info.points = (student_info.points or 0) + points
            # 记录积分历史
            points_history = PointsHistory(
                student_id=student_info.id,
                points=points,
                reason=f"参与活动：{activity.title}",
                activity_id=activity.id
            )
            db.session.add(points_history)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'签到成功！获得 {points} 积分'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in checkin: {e}")
        return jsonify({
            'success': False,
            'message': '签到失败，请重试'
        }), 500

# 一个辅助函数，确保时间的时区一致性
def get_localized_now():
    """获取本地时间，与数据库中的时间使用相同的时区处理方式"""
    # 因为数据库中存储的是datetime.now()，所以我们也使用相同的方式
    return datetime.now()
