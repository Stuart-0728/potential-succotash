from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from src.models import db, Activity, Registration, User, StudentInfo
from datetime import datetime, timedelta
import logging

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
        # 获取学生已报名的活动
        registered_activities = Activity.query.join(
            Registration, Activity.id == Registration.activity_id
        ).filter(
            Registration.user_id == current_user.id,
            Registration.status == 'registered'  # 确保只获取有效报名
        ).all()
        
        # 获取即将开始的活动（未报名）
        upcoming_activities = Activity.query.filter(
            Activity.status == 'active',
            Activity.registration_deadline >= datetime.now()
        ).outerjoin(
            Registration, (Activity.id == Registration.activity_id) & (Registration.user_id == current_user.id)
        ).filter(
            (Registration.id == None) | (Registration.status == 'cancelled')
        ).order_by(
            Activity.registration_deadline
        ).limit(5).all()
        
        # 获取学生通知
        notifications = []
        
        # 即将开始的已报名活动通知
        upcoming_registered = Activity.query.join(
            Registration, Activity.id == Registration.activity_id
        ).filter(
            Registration.user_id == current_user.id,
            Registration.status == 'registered',
            Activity.start_time > datetime.now(),
            Activity.start_time <= datetime.now() + timedelta(days=3)
        ).all()
        
        for activity in upcoming_registered:
            time_diff = activity.start_time - datetime.now()
            days = time_diff.days
            hours = time_diff.seconds // 3600
            
            if days > 0:
                time_text = f"{days}天{hours}小时"
            else:
                time_text = f"{hours}小时"
                
            notifications.append({
                'type': 'upcoming',
                'message': f'您报名的活动"{activity.title}"将在{time_text}后开始',
                'time': datetime.now(),
                'link': url_for('student.activity_detail', id=activity.id)
            })
        
        # 即将截止报名的活动通知
        closing_soon = Activity.query.filter(
            Activity.status == 'active',
            Activity.registration_deadline > datetime.now(),
            Activity.registration_deadline <= datetime.now() + timedelta(days=1)
        ).outerjoin(
            Registration, (Activity.id == Registration.activity_id) & (Registration.user_id == current_user.id)
        ).filter(
            (Registration.id == None) | (Registration.status == 'cancelled')
        ).all()
        
        for activity in closing_soon:
            time_diff = activity.registration_deadline - datetime.now()
            hours = time_diff.seconds // 3600
            minutes = (time_diff.seconds % 3600) // 60
            
            if hours > 0:
                time_text = f"{hours}小时{minutes}分钟"
            else:
                time_text = f"{minutes}分钟"
                
            notifications.append({
                'type': 'closing',
                'message': f'活动"{activity.title}"将在{time_text}后截止报名',
                'time': datetime.now(),
                'link': url_for('student.activity_detail', id=activity.id)
            })
        
        # 最新活动通知
        new_activities = Activity.query.filter(
            Activity.status == 'active',
            Activity.created_at >= datetime.now() - timedelta(days=3)
        ).order_by(Activity.created_at.desc()).limit(3).all()
        
        for activity in new_activities:
            notifications.append({
                'type': 'new',
                'message': f'新活动发布："{activity.title}"',
                'time': activity.created_at,
                'link': url_for('student.activity_detail', id=activity.id)
            })
        
        # 按时间排序通知
        notifications.sort(key=lambda x: x['time'], reverse=True)
        
        return render_template('student/dashboard.html', 
                              registered_activities=registered_activities,
                              upcoming_activities=upcoming_activities,
                              notifications=notifications,
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
        
        # 检查用户是否已报名
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
        
        return render_template('student/activity_detail.html', 
                              activity=activity,
                              registration=registration,
                              can_register=can_register,
                              now=datetime.now())
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
