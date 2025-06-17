from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file, current_app
from flask_login import login_required, current_user
from src.models import User, Activity, Registration, StudentInfo, db, Tag
from src.routes.utils import admin_required, log_action
from datetime import datetime, timedelta
import pandas as pd
import io
import logging
import json
from sqlalchemy import func, desc, and_
from src.forms import ActivityForm, SearchForm
import os
import shutil
from werkzeug.utils import secure_filename

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
    try:
        form = ActivityForm()
        # 动态加载标签选项
        form.tags.choices = [(tag.id, tag.name) for tag in Tag.query.order_by(Tag.name).all()]
        
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
                
                # 添加标签
                for tag_id in form.tags.data:
                    tag = Tag.query.get(tag_id)
                    if tag:
                        activity.tags.append(tag)
                
                # 处理海报上传
                if form.poster.data:
                    poster = form.poster.data
                    filename = secure_filename(poster.filename)
                    poster.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                    activity.poster_url = url_for('static', filename=f'uploads/posters/{filename}')
                
                db.session.add(activity)
                db.session.commit()
                
                flash('活动创建成功', 'success')
                log_action('create_activity', f'创建活动: {activity.title}')
                return redirect(url_for('admin.activity_view', id=activity.id))
            
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error creating activity: {e}")
                flash('创建活动失败', 'danger')
        
        return render_template('admin/activity_form.html', form=form, title='创建新活动')
    except Exception as e:
        logger.error(f"Error in create_activity view: {e}")
        flash('加载创建活动页面时出错', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/activity/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_activity(id):
    try:
        activity = Activity.query.get_or_404(id)
        form = ActivityForm(obj=activity)
        
        if request.method == 'POST' and form.validate_on_submit():
            try:
                form.populate_obj(activity)
                # 处理标签
                activity.tags.clear()
                for tag_id in form.tags.data:
                    tag = Tag.query.get(tag_id)
                    if tag:
                        activity.tags.append(tag)
                
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
def activity_view(id):
    try:
        activity = Activity.query.get_or_404(id)
        # 获取创建者信息
        creator = User.query.get(activity.created_by)
        
        # 获取报名人数
        registration_count = Registration.query.filter_by(activity_id=id).count()
        
        # 获取报名学生列表
        registrations = Registration.query.filter_by(activity_id=id).join(
            User, Registration.user_id == User.id
        ).join(
            StudentInfo, User.id == StudentInfo.user_id
        ).add_columns(
            StudentInfo.real_name,
            StudentInfo.student_id,
            StudentInfo.grade,
            StudentInfo.college,
            StudentInfo.major
        ).all()

        return render_template('admin/activity_view.html', 
                             activity=activity, 
                             creator=creator, 
                             registration_count=registration_count,
                             registrations=registrations)
    except Exception as e:
        logger.error(f"Error viewing activity: {e}")
        flash('查看活动详情时出错', 'danger')
        return redirect(url_for('admin.activities'))

@admin_bp.route('/activity/<int:id>/delete', methods=['POST'])
@admin_required
def delete_activity(id):
    try:
        activity = Activity.query.get_or_404(id)
        force_delete = request.args.get('force', 'false').lower() == 'true'
        
        # 如果是从活动详情页面删除，或者没有人报名，则直接删除
        if force_delete or Registration.query.filter_by(activity_id=activity.id).count() == 0:
            db.session.delete(activity)
            db.session.commit()
            log_action('delete_activity', f'删除活动: {activity.title}')
            flash('活动已删除', 'success')
        else:
            # 如果是从活动列表页面删除且有人报名，则标记为已取消
            activity.status = 'cancelled'
            db.session.commit()
            log_action('cancel_activity', f'取消活动: {activity.title}')
            flash('活动已标记为已取消', 'success')
        
        # 根据来源页面返回
        referer = request.headers.get('Referer', '')
        if 'activity/view' in referer:
            return redirect(url_for('admin.activities'))
        return redirect(request.referrer or url_for('admin.activities'))
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
            StudentInfo.phone,
            StudentInfo.points,  # 新增积分
            Registration.check_in_time  # 新增签到时间
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
                '状态': '已报名' if reg.status == 'registered' else '已取消' if reg.status == 'cancelled' else '已参加',
                '积分': reg.points,
                '签到状态': '已签到' if reg.check_in_time else '未签到',
                '签到时间': reg.check_in_time.strftime('%Y-%m-%d %H:%M:%S') if reg.check_in_time else ''
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

@admin_bp.route('/backup', methods=['GET'])
@admin_required
def backup_system():
    try:
        # 获取备份目录中的备份文件列表
        backup_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backups')
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        backups = []
        for filename in os.listdir(backup_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(backup_dir, filename)
                backup_time = datetime.fromtimestamp(os.path.getctime(filepath))
                backups.append({
                    'name': filename,
                    'created_at': backup_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'size': f"{os.path.getsize(filepath) / 1024:.1f} KB"
                })
        
        backups.sort(key=lambda x: x['created_at'], reverse=True)
        current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        return render_template('admin/backup.html', 
                             backups=backups, 
                             current_time=current_time)
    except Exception as e:
        logger.error(f"Error in backup system page: {e}")
        flash('加载备份页面时出错', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/backup/create', methods=['POST'])
@admin_required
def create_backup():
    try:
        backup_name = request.form.get('backup_name', f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        include_users = 'include_users' in request.form
        include_activities = 'include_activities' in request.form
        include_registrations = 'include_registrations' in request.form
        
        # 创建备份数据
        backup_data = {
            'created_at': datetime.now().isoformat(),
            'created_by': current_user.id,
            'data': {}
        }
        
        if include_users:
            users = User.query.all()
            backup_data['data']['users'] = [
                {c.name: getattr(user, c.name) for c in User.__table__.columns}
                for user in users
            ]
            
            student_info = StudentInfo.query.all()
            backup_data['data']['student_info'] = [
                {c.name: getattr(info, c.name) for c in StudentInfo.__table__.columns}
                for info in student_info
            ]
        
        if include_activities:
            activities = Activity.query.all()
            backup_data['data']['activities'] = [
                {c.name: getattr(activity, c.name) for c in Activity.__table__.columns}
                for activity in activities
            ]
        
        if include_registrations:
            registrations = Registration.query.all()
            backup_data['data']['registrations'] = [
                {c.name: getattr(reg, c.name) for c in Registration.__table__.columns}
                for reg in registrations
            ]
        
        # 保存备份文件
        backup_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backups')
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        filename = secure_filename(f"{backup_name}.json")
        filepath = os.path.join(backup_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
        
        flash('备份创建成功', 'success')
        log_action('create_backup', f'创建系统备份: {filename}')
        return redirect(url_for('admin.backup_system'))
    
    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        flash('创建备份失败', 'danger')
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

@admin_bp.route('/activity/<int:id>/checkin', methods=['POST'])
@admin_required
def activity_checkin(id):
    try:
        activity = Activity.query.get_or_404(id)
        student_id = request.form.get('student_id')
        
        if not student_id:
            return jsonify({'success': False, 'message': '请提供学生ID'})
        
        registration = Registration.query.filter_by(
            activity_id=activity.id,
            user_id=student_id,
            status='registered'
        ).first()
        
        if not registration:
            return jsonify({'success': False, 'message': '未找到该学生的报名记录'})
        
        # 更新签到状态
        registration.status = 'checked_in'
        registration.check_in_time = datetime.utcnow()
        
        # 添加积分奖励
        points = 20 if activity.is_featured else 10  # 重点活动给20分，普通活动给10分
        student_info = StudentInfo.query.filter_by(user_id=student_id).first()
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
        bin_counts = [0]*(len(points_bins))
        for stu in StudentInfo.query.all():
            for i, b in enumerate(points_bins):
                if i == len(points_bins)-1:
                    if stu.points >= b:
                        bin_counts[i] += 1
                elif b <= stu.points < points_bins[i+1]:
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
