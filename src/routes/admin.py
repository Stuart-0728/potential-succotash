from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import login_required, current_user
from src.models import User, Activity, Registration, StudentInfo, db
from src.routes.utils import admin_required, log_action
from datetime import datetime, timedelta
import pandas as pd
import io
import logging
import json
from sqlalchemy import func, desc, and_
from src.forms import ActivityForm, SearchForm

admin_bp = Blueprint('admin', __name__)
logger = logging.getLogger(__name__)

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    try:
        # 获取基本统计数据
        total_students = User.query.filter_by(role_id=2).count()
        total_activities = Activity.query.count()
        active_activities = Activity.query.filter_by(status='active').count()
        
        # 获取最近活动
        recent_activities = Activity.query.order_by(Activity.created_at.desc()).limit(5).all()
        
        # 获取最近注册的学生
        recent_students = User.query.filter_by(role_id=2).order_by(User.created_at.desc()).limit(5).all()
        
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
        per_page = 10
        
        # 根据状态筛选活动
        if status == 'active':
            query = Activity.query.filter_by(status='active')
        elif status == 'completed':
            query = Activity.query.filter_by(status='completed')
        elif status == 'cancelled':
            query = Activity.query.filter_by(status='cancelled')
        else:
            query = Activity.query
            status = 'all'  # 确保状态值有效
        
        # 分页查询
        activities = query.order_by(Activity.start_time.desc()).paginate(page=page, per_page=per_page)
        
        return render_template('admin/activities.html', activities=activities, current_status=status)
    except Exception as e:
        logger.error(f"Error in activities: {e}")
        flash('加载活动列表时出错', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/activity/create', methods=['GET', 'POST'])
@admin_required
def create_activity():
    form = ActivityForm()
    
    if request.method == 'POST' and form.validate_on_submit():
        try:
            # 创建新活动
            activity = Activity(
                title=form.title.data,
                description=form.description.data,
                location=form.location.data,
                start_time=form.start_time.data,
                end_time=form.end_time.data,
                registration_deadline=form.registration_deadline.data,
                max_participants=form.max_participants.data,
                status=form.status.data,
                created_by=current_user.id
            )
            
            # 处理海报上传
            if form.poster.data:
                poster = form.poster.data
                # 保存文件
                import os
                from werkzeug.utils import secure_filename
                filename = secure_filename(poster.filename)
                # 确保上传目录存在
                upload_dir = os.path.join('src/static/uploads/posters')
                os.makedirs(upload_dir, exist_ok=True)
                poster_path = os.path.join(upload_dir, filename)
                poster.save(poster_path)
                activity.poster = 'uploads/posters/' + filename
            
            db.session.add(activity)
            db.session.commit()
            
            log_action('create_activity', f'创建活动: {activity.title}')
            flash('活动创建成功', 'success')
            return redirect(url_for('admin.activities'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating activity: {e}")
            flash(f'创建活动时出错: {str(e)}', 'danger')
    
    return render_template('admin/activity_form.html', form=form, activity=None)

@admin_bp.route('/activity/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_activity(id):
    try:
        activity = Activity.query.get_or_404(id)
        form = ActivityForm(obj=activity)
        
        if request.method == 'POST' and form.validate_on_submit():
            try:
                form.populate_obj(activity)
                
                # 处理海报上传
                if form.poster.data:
                    poster = form.poster.data
                    # 保存文件
                    import os
                    from werkzeug.utils import secure_filename
                    filename = secure_filename(poster.filename)
                    # 确保上传目录存在
                    upload_dir = os.path.join('src/static/uploads/posters')
                    os.makedirs(upload_dir, exist_ok=True)
                    poster_path = os.path.join(upload_dir, filename)
                    poster.save(poster_path)
                    activity.poster = 'uploads/posters/' + filename
                
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
def view_activity(id):
    try:
        activity = Activity.query.get_or_404(id)
        return render_template('admin/activity_view.html', activity=activity)
    except Exception as e:
        logger.error(f"Error viewing activity: {e}")
        flash('查看活动详情时出错', 'danger')
        return redirect(url_for('admin.activities'))

@admin_bp.route('/activity/<int:id>/delete', methods=['POST'])
@admin_required
def delete_activity(id):
    try:
        activity = Activity.query.get_or_404(id)
        
        # 如果有人报名，则标记为已取消而不是删除
        if Registration.query.filter_by(activity_id=activity.id).count() > 0:
            activity.status = 'cancelled'
            db.session.commit()
            log_action('cancel_activity', f'取消活动: {activity.title}')
            flash('活动已标记为已取消', 'success')
        else:
            db.session.delete(activity)
            db.session.commit()
            log_action('delete_activity', f'删除活动: {activity.title}')
            flash('活动已删除', 'success')
        
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
        per_page = 10
        search_query = request.args.get('q', '')
        
        # 构建查询
        query = User.query.filter_by(role_id=2).join(
            StudentInfo, User.id == StudentInfo.user_id
        )
        
        # 搜索功能
        if search_query:
            query = query.filter(
                (User.username.like(f'%{search_query}%')) |
                (StudentInfo.real_name.like(f'%{search_query}%')) |
                (StudentInfo.student_id.like(f'%{search_query}%'))
            )
        
        # 分页查询
        students = query.paginate(page=page, per_page=per_page)
        
        return render_template('admin/students.html', students=students, search_query=search_query)
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
        thirty_days_ago = datetime.now() - timedelta(days=30)
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
            date = datetime.now() - timedelta(days=i)
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
            current_month = datetime.now().replace(day=1) - timedelta(days=i*30)
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
            StudentInfo.phone
        ).all()
        
        # 统计报名状态
        registered_count = Registration.query.filter_by(activity_id=id, status='registered').count()
        cancelled_count = Registration.query.filter_by(activity_id=id, status='cancelled').count()
        attended_count = Registration.query.filter_by(activity_id=id, status='attended').count()
        
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
            Registration.status,
            StudentInfo.real_name,
            StudentInfo.student_id,
            StudentInfo.grade,
            StudentInfo.college,
            StudentInfo.major,
            StudentInfo.phone
        ).all()
        
        # 创建Excel文件
        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine='openpyxl')
        
        # 转换为DataFrame
        data = []
        for reg in registrations:
            data.append({
                '报名ID': reg.registration_id,
                '姓名': reg.real_name,
                '学号': reg.student_id,
                '年级': reg.grade,
                '学院': reg.college,
                '专业': reg.major,
                '手机号': reg.phone,
                '报名时间': reg.register_time.strftime('%Y-%m-%d %H:%M:%S'),
                '状态': '已报名' if reg.status == 'registered' else '已取消' if reg.status == 'cancelled' else '已参加'
            })
        
        df = pd.DataFrame(data)
        df.to_excel(writer, sheet_name='报名信息', index=False)
        
        # 保存Excel
        writer.close()
        output.seek(0)
        
        # 记录操作日志
        log_action('export_registrations', f'导出活动报名信息: {activity.title}')
        
        # 返回Excel文件
        return send_file(
            output,
            as_attachment=True,
            download_name=f"{activity.title}_报名信息_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx",
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
            StudentInfo.qq
        ).all()
        
        # 创建Excel文件
        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine='openpyxl')
        
        # 转换为DataFrame
        data = []
        for student in students:
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
                '注册时间': student.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        df = pd.DataFrame(data)
        df.to_excel(writer, sheet_name='学生信息', index=False)
        
        # 保存Excel
        writer.close()
        output.seek(0)
        
        # 记录操作日志
        log_action('export_students', '导出所有学生信息')
        
        # 返回Excel文件
        return send_file(
            output,
            as_attachment=True,
            download_name=f"学生信息_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx",
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        logger.error(f"Error exporting students: {e}")
        flash('导出学生信息时出错', 'danger')
        return redirect(url_for('admin.students'))

# 添加备份功能的占位路由，避免模板中的链接报错
@admin_bp.route('/backup')
@admin_required
def backup():
    flash('数据备份功能正在开发中', 'info')
    return redirect(url_for('admin.dashboard'))

# 添加系统日志功能的占位路由，避免模板中的链接报错
@admin_bp.route('/system_logs')
@admin_required
def system_logs():
    flash('系统日志功能正在开发中', 'info')
    return redirect(url_for('admin.dashboard'))

# 添加更新报名状态的路由
@admin_bp.route('/registration/<int:id>/update_status', methods=['POST'])
@admin_required
def update_registration_status(id):
    try:
        registration = Registration.query.get_or_404(id)
        new_status = request.form.get('status')
        
        if new_status not in ['registered', 'cancelled', 'attended']:
            flash('无效的状态值', 'danger')
            return redirect(url_for('admin.activity_registrations', id=registration.activity_id))
        
        registration.status = new_status
        db.session.commit()
        
        log_action('update_registration', f'更新报名状态: ID {id} 到 {new_status}')
        flash('报名状态已更新', 'success')
        return redirect(url_for('admin.activity_registrations', id=registration.activity_id))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating registration status: {e}")
        flash('更新报名状态时出错', 'danger')
        return redirect(url_for('admin.dashboard'))
