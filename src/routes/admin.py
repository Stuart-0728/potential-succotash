from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_file, jsonify, abort
from flask_login import login_required, current_user
from src.models import db, Activity, Registration, User, StudentInfo, Role
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import logging
import pandas as pd
import io
from src.routes.utils import admin_required, log_action

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    try:
        # 获取基本统计数据
        total_activities = Activity.query.count()
        active_activities = Activity.query.filter_by(status='active').count()
        total_students = User.query.join(Role).filter(Role.name == 'Student').count()
        total_registrations = Registration.query.filter_by(status='registered').count()
        
        # 获取最近活动
        recent_activities = Activity.query.order_by(Activity.created_at.desc()).limit(5).all()
        
        # 获取最近报名
        recent_registrations = Registration.query.join(
            User, Registration.user_id == User.id
        ).join(
            StudentInfo, User.id == StudentInfo.user_id
        ).join(
            Activity, Registration.activity_id == Activity.id
        ).add_columns(
            User.username,
            StudentInfo.real_name,
            StudentInfo.student_id,
            Activity.title,
            Registration.register_time
        ).order_by(Registration.register_time.desc()).limit(10).all()
        
        return render_template('admin/dashboard.html',
                              total_activities=total_activities,
                              active_activities=active_activities,
                              total_students=total_students,
                              total_registrations=total_registrations,
                              recent_activities=recent_activities,
                              recent_registrations=recent_registrations)
    except Exception as e:
        logger.error(f"Error in admin dashboard: {e}")
        flash('加载管理面板时发生错误', 'danger')
        return redirect(url_for('main.index'))

@admin_bp.route('/activities')
@admin_required
def activities():
    try:
        page = request.args.get('page', 1, type=int)
        status = request.args.get('status', 'all')
        search = request.args.get('search', '')
        
        # 基本查询
        query = Activity.query
        
        # 搜索过滤
        if search:
            query = query.filter(
                db.or_(
                    Activity.title.ilike(f'%{search}%'),
                    Activity.location.ilike(f'%{search}%')
                )
            )
        
        # 状态过滤
        if status == 'active':
            query = query.filter(Activity.status == 'active')
        elif status == 'completed':
            query = query.filter(Activity.status == 'completed')
        elif status == 'cancelled':
            query = query.filter(Activity.status == 'cancelled')
        
        # 获取活动列表
        activities_list = query.order_by(Activity.created_at.desc()).paginate(page=page, per_page=10)
        
        return render_template('admin/activities.html', 
                              activities=activities_list, 
                              current_status=status,
                              search=search)
    except Exception as e:
        logger.error(f"Error in admin activities: {e}")
        flash('加载活动列表时发生错误', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/activity/<int:id>')
@admin_required
def view_activity(id):
    try:
        activity = Activity.query.get_or_404(id)
        
        # 获取创建者信息
        creator = User.query.get(activity.created_by) if activity.created_by else None
        
        # 获取报名人数
        registration_count = Registration.query.filter_by(
            activity_id=activity.id,
            status='registered'
        ).count()
        
        return render_template('admin/activity_view.html', 
                              activity=activity,
                              creator=creator,
                              registration_count=registration_count)
    except Exception as e:
        logger.error(f"Error in view_activity: {e}")
        flash('查看活动详情时发生错误', 'danger')
        return redirect(url_for('admin.activities'))

@admin_bp.route('/activity/create', methods=['GET', 'POST'])
@admin_required
def create_activity():
    try:
        from src.forms import ActivityForm
        
        form = ActivityForm()
        
        if form.validate_on_submit():
            activity = Activity(
                title=form.title.data,
                description=form.description.data,
                location=form.location.data,
                start_time=form.start_time.data,
                end_time=form.end_time.data,
                registration_deadline=form.registration_deadline.data,
                max_participants=form.max_participants.data,
                created_by=current_user.id,
                status='active'
            )
            
            # 处理海报上传
            if form.poster.data:
                poster_filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{form.poster.data.filename}")
                poster_path = os.path.join(current_app.root_path, 'static/uploads/posters', poster_filename)
                
                # 确保目录存在
                os.makedirs(os.path.dirname(poster_path), exist_ok=True)
                
                try:
                    # 保存文件
                    form.poster.data.save(poster_path)
                    # 设置文件权限确保可读
                    os.chmod(poster_path, 0o644)
                    activity.poster_path = poster_filename
                    logger.info(f"海报上传成功: {poster_filename}")
                except Exception as e:
                    logger.error(f"海报上传失败: {e}")
                    flash(f'海报上传失败: {str(e)}', 'warning')
            
            db.session.add(activity)
            db.session.commit()
            
            # 记录日志
            log_action(
                current_user.id,
                'create_activity',
                f'创建活动: {activity.title}'
            )
            
            flash('活动创建成功！', 'success')
            return redirect(url_for('admin.activities'))
        
        return render_template('admin/activity_form.html', form=form, is_edit=False)
    except Exception as e:
        logger.error(f"Error in create_activity: {e}")
        db.session.rollback()
        flash('创建活动时发生错误', 'danger')
        return redirect(url_for('admin.activities'))

@admin_bp.route('/activity/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_activity(id):
    try:
        from src.forms import ActivityForm
        
        activity = Activity.query.get_or_404(id)
        form = ActivityForm(obj=activity)
        
        if form.validate_on_submit():
            activity.title = form.title.data
            activity.description = form.description.data
            activity.location = form.location.data
            activity.start_time = form.start_time.data
            activity.end_time = form.end_time.data
            activity.registration_deadline = form.registration_deadline.data
            activity.max_participants = form.max_participants.data
            activity.status = form.status.data
            
            # 处理海报上传 - 修复图片上传问题
            if form.poster.data and form.poster.data.filename:
                # 删除旧海报
                if activity.poster_path:
                    old_poster_path = os.path.join(current_app.root_path, 'static/uploads/posters', activity.poster_path)
                    if os.path.exists(old_poster_path):
                        try:
                            os.remove(old_poster_path)
                        except Exception as e:
                            logger.error(f"删除旧海报失败: {e}")
                
                # 上传新海报
                poster_filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{form.poster.data.filename}")
                poster_path = os.path.join(current_app.root_path, 'static/uploads/posters', poster_filename)
                
                # 确保目录存在
                os.makedirs(os.path.dirname(poster_path), exist_ok=True)
                
                try:
                    # 保存文件
                    form.poster.data.save(poster_path)
                    # 设置文件权限确保可读
                    os.chmod(poster_path, 0o644)
                    activity.poster_path = poster_filename
                    logger.info(f"海报上传成功: {poster_filename}")
                except Exception as e:
                    logger.error(f"海报上传失败: {e}")
                    flash(f'海报上传失败: {str(e)}', 'warning')
            
            activity.updated_at = datetime.now()
            db.session.commit()
            
            # 记录日志
            log_action(
                current_user.id,
                'edit_activity',
                f'编辑活动: {activity.title}'
            )
            
            flash('活动更新成功！', 'success')
            return redirect(url_for('admin.view_activity', id=activity.id))
        
        return render_template('admin/activity_form.html', form=form, activity=activity, is_edit=True)
    except Exception as e:
        logger.error(f"Error in edit_activity: {e}")
        db.session.rollback()
        flash('编辑活动时发生错误', 'danger')
        return redirect(url_for('admin.activities'))

@admin_bp.route('/activity/<int:id>/delete', methods=['POST'])
@admin_required
def delete_activity(id):
    try:
        activity = Activity.query.get_or_404(id)
        
        # 检查是否有人报名
        registrations = Registration.query.filter_by(activity_id=id).count()
        
        if registrations > 0:
            # 如果有人报名，则标记为已取消而不是删除
            activity.status = 'cancelled'
            db.session.commit()
            
            # 记录日志
            log_action(
                current_user.id,
                'cancel_activity',
                f'取消活动: {activity.title} (有{registrations}人报名)'
            )
            
            flash(f'活动已标记为已取消。该活动有{registrations}人报名，因此未被彻底删除。', 'warning')
        else:
            # 删除海报文件
            if activity.poster_path:
                poster_path = os.path.join(current_app.root_path, 'static/uploads/posters', activity.poster_path)
                if os.path.exists(poster_path):
                    try:
                        os.remove(poster_path)
                    except Exception as e:
                        logger.error(f"删除海报失败: {e}")
            
            # 记录日志
            activity_title = activity.title
            
            # 删除活动
            db.session.delete(activity)
            db.session.commit()
            
            log_action(
                current_user.id,
                'delete_activity',
                f'删除活动: {activity_title}'
            )
            
            flash('活动已成功删除！', 'success')
        
        return redirect(url_for('admin.activities'))
    except Exception as e:
        logger.error(f"Error in delete_activity: {e}")
        db.session.rollback()
        flash('删除活动时发生错误', 'danger')
        return redirect(url_for('admin.activities'))

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
            Registration.id.label('id'),
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
        registered_count = sum(1 for r in registrations if r.status == 'registered')
        cancelled_count = sum(1 for r in registrations if r.status == 'cancelled')
        attended_count = sum(1 for r in registrations if r.status == 'attended')
        
        return render_template('admin/activity_registrations.html',
                              activity=activity,
                              registrations=registrations,
                              registered_count=registered_count,
                              cancelled_count=cancelled_count,
                              attended_count=attended_count)
    except Exception as e:
        logger.error(f"Error in activity_registrations: {e}")
        flash('查看报名情况时发生错误', 'danger')
        return redirect(url_for('admin.activities'))

@admin_bp.route('/activity/<int:id>/export')
@admin_required
def export_registrations(id):
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
            Registration.register_time,
            Registration.status,
            User.username,
            StudentInfo.real_name,
            StudentInfo.student_id,
            StudentInfo.grade,
            StudentInfo.college,
            StudentInfo.major,
            StudentInfo.phone,
            StudentInfo.qq
        ).order_by(Registration.register_time).all()
        
        # 创建DataFrame
        data = []
        for reg in registrations:
            status_text = "已报名"
            if reg.status == 'cancelled':
                status_text = "已取消"
            elif reg.status == 'attended':
                status_text = "已参加"
                
            data.append({
                '用户名': reg.username,
                '姓名': reg.real_name,
                '学号': reg.student_id,
                '年级': reg.grade,
                '学院': reg.college,
                '专业': reg.major,
                '手机号': reg.phone,
                'QQ号': reg.qq,
                '报名时间': reg.register_time.strftime('%Y-%m-%d %H:%M:%S') if reg.register_time else '',
                '状态': status_text
            })
        
        df = pd.DataFrame(data)
        
        # 创建Excel文件
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='报名学生')
            
            # 自动调整列宽
            worksheet = writer.sheets['报名学生']
            for i, col in enumerate(df.columns):
                max_length = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.column_dimensions[chr(65 + i)].width = max_length
        
        output.seek(0)
        
        # 记录日志
        log_action(
            current_user.id,
            'export_registrations',
            f'导出活动报名: {activity.title}'
        )
        
        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f"{activity.title}_报名学生_{timestamp}.xlsx"
        filename = secure_filename(filename)
        
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        logger.error(f"Error in export_registrations: {e}")
        flash('导出报名数据时发生错误', 'danger')
        return redirect(url_for('admin.activity_registrations', id=id))

@admin_bp.route('/students')
@admin_required
def students():
    try:
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '')
        
        # 基本查询 - 修复学生管理页面查询
        query = User.query.join(Role).filter(Role.name == 'Student')
        
        # 搜索过滤 - 修复搜索功能
        if search:
            query = query.join(StudentInfo, User.id == StudentInfo.user_id).filter(
                db.or_(
                    StudentInfo.real_name.ilike(f'%{search}%'),
                    StudentInfo.student_id.ilike(f'%{search}%'),
                    StudentInfo.college.ilike(f'%{search}%'),
                    StudentInfo.major.ilike(f'%{search}%')
                )
            )
        else:
            # 确保无论是否搜索，都加载student_info关系
            query = query.join(StudentInfo, User.id == StudentInfo.user_id)
        
        # 获取学生列表，确保加载student_info关系
        students_list = query.order_by(User.created_at.desc()).paginate(page=page, per_page=10)
        
        return render_template('admin/students.html', 
                              students=students_list,
                              search=search)
    except Exception as e:
        logger.error(f"Error in admin students: {e}")
        flash('加载学生列表时发生错误', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/students/export')
@admin_required
def export_students():
    try:
        # 获取所有学生
        students = User.query.join(Role).filter(Role.name == 'Student').join(
            StudentInfo, User.id == StudentInfo.user_id
        ).add_columns(
            User.username,
            User.email,
            User.created_at,
            User.last_login,
            StudentInfo.real_name,
            StudentInfo.student_id,
            StudentInfo.grade,
            StudentInfo.college,
            StudentInfo.major,
            StudentInfo.phone,
            StudentInfo.qq
        ).all()
        
        # 创建DataFrame
        data = []
        for student in students:
            data.append({
                '用户名': student.username,
                '邮箱': student.email,
                '姓名': student.real_name,
                '学号': student.student_id,
                '年级': student.grade,
                '学院': student.college,
                '专业': student.major,
                '手机号': student.phone,
                'QQ号': student.qq,
                '注册时间': student.created_at.strftime('%Y-%m-%d %H:%M:%S') if student.created_at else '',
                '最后登录': student.last_login.strftime('%Y-%m-%d %H:%M:%S') if student.last_login else ''
            })
        
        df = pd.DataFrame(data)
        
        # 创建Excel文件
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='学生信息')
            
            # 自动调整列宽
            worksheet = writer.sheets['学生信息']
            for i, col in enumerate(df.columns):
                max_length = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.column_dimensions[chr(65 + i)].width = max_length
        
        output.seek(0)
        
        # 记录日志
        log_action(
            current_user.id,
            'export_students',
            f'导出学生信息'
        )
        
        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f"学生信息_{timestamp}.xlsx"
        
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        logger.error(f"Error in export_students: {e}")
        flash('导出学生数据时发生错误', 'danger')
        return redirect(url_for('admin.students'))

@admin_bp.route('/student/<int:id>')
@admin_required
def view_student(id):
    try:
        user = User.query.get_or_404(id)
        
        # 确保是学生
        if not user.role or user.role.name != 'Student':
            flash('该用户不是学生', 'warning')
            return redirect(url_for('admin.students'))
        
        # 获取学生信息
        student_info = StudentInfo.query.filter_by(user_id=id).first()
        
        if not student_info:
            flash('未找到该学生的详细信息', 'warning')
            return redirect(url_for('admin.students'))
        
        # 获取报名活动
        registrations = Registration.query.filter_by(
            user_id=id
        ).join(
            Activity, Registration.activity_id == Activity.id
        ).add_columns(
            Registration.id,
            Registration.register_time,
            Registration.status,
            Activity.id.label('activity_id'),
            Activity.title,
            Activity.start_time,
            Activity.status.label('activity_status')
        ).order_by(Registration.register_time.desc()).all()
        
        return render_template('admin/student_view.html',
                              user=user,
                              student_info=student_info,
                              registrations=registrations)
    except Exception as e:
        logger.error(f"Error in view_student: {e}")
        flash('查看学生详情时发生错误', 'danger')
        return redirect(url_for('admin.students'))

@admin_bp.route('/student/<int:id>/delete', methods=['POST'])
@admin_required
def delete_student(id):
    try:
        user = User.query.get_or_404(id)
        
        # 确保是学生
        if not user.role or user.role.name != 'Student':
            flash('该用户不是学生', 'warning')
            return redirect(url_for('admin.students'))
        
        # 获取学生信息
        student_info = StudentInfo.query.filter_by(user_id=id).first()
        
        # 记录日志
        username = user.username
        real_name = student_info.real_name if student_info else '未知'
        
        # 检查是否有活动报名
        registrations = Registration.query.filter_by(user_id=id).all()
        
        # 删除报名记录
        for reg in registrations:
            db.session.delete(reg)
        
        # 删除学生信息
        if student_info:
            db.session.delete(student_info)
        
        # 删除用户
        db.session.delete(user)
        db.session.commit()
        
        log_action(
            current_user.id,
            'delete_student',
            f'删除学生: {username} ({real_name})'
        )
        
        flash('学生账号已成功删除！', 'success')
        return redirect(url_for('admin.students'))
    except Exception as e:
        logger.error(f"Error in delete_student: {e}")
        db.session.rollback()
        flash('删除学生账号时发生错误', 'danger')
        return redirect(url_for('admin.students'))

@admin_bp.route('/statistics')
@admin_required
def statistics():
    try:
        return render_template('admin/statistics.html')
    except Exception as e:
        logger.error(f"Error in statistics: {e}")
        flash('加载统计数据时发生错误', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/system_logs')
@admin_required
def system_logs():
    try:
        page = request.args.get('page', 1, type=int)
        
        # 获取系统日志
        logs = []
        log_file = os.path.join(current_app.root_path, 'logs/app.log')
        
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                logs = f.readlines()
            
            # 反转顺序，最新的在前面
            logs.reverse()
        
        # 简单分页
        per_page = 50
        total_pages = (len(logs) + per_page - 1) // per_page
        page = min(max(page, 1), total_pages)
        
        start = (page - 1) * per_page
        end = min(start + per_page, len(logs))
        
        current_logs = logs[start:end]
        
        return render_template('admin/system_logs.html',
                              logs=current_logs,
                              page=page,
                              total_pages=total_pages)
    except Exception as e:
        logger.error(f"Error in system_logs: {e}")
        flash('加载系统日志时发生错误', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/backup')
@admin_required
def backup():
    try:
        # 获取备份文件列表
        backup_dir = os.path.join(current_app.root_path, 'backups')
        
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        backup_files = []
        for file in os.listdir(backup_dir):
            if file.endswith('.db') or file.endswith('.sql'):
                file_path = os.path.join(backup_dir, file)
                file_size = os.path.getsize(file_path)
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                backup_files.append({
                    'name': file,
                    'size': file_size,
                    'time': file_time
                })
        
        # 按时间排序，最新的在前面
        backup_files.sort(key=lambda x: x['time'], reverse=True)
        
        return render_template('admin/backup.html',
                              backup_files=backup_files)
    except Exception as e:
        logger.error(f"Error in backup: {e}")
        flash('加载备份页面时发生错误', 'danger')
        return redirect(url_for('admin.dashboard'))
