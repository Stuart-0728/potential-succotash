from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from src import db
from src.models import User, Role, StudentInfo, Tag, StudentInterestTag, AIUserPreferences, SystemLog
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, ValidationError
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp
from datetime import datetime
import logging

# 配置日志
logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

# 注册表单
class RegistrationForm(FlaskForm):
    username = StringField('用户名', validators=[
        DataRequired(message='用户名不能为空'),
        Length(min=3, max=20, message='用户名长度必须在3-20个字符之间'),
        Regexp('^[A-Za-z0-9_]*$', message='用户名只能包含字母、数字和下划线')
    ])
    email = StringField('邮箱', validators=[
        DataRequired(message='邮箱不能为空'),
        Email(message='请输入有效的邮箱地址')
    ])
    password = PasswordField('密码', validators=[
        DataRequired(message='密码不能为空'),
        Length(min=6, message='密码长度不能少于6个字符')
    ])
    confirm_password = PasswordField('确认密码', validators=[
        DataRequired(message='确认密码不能为空'),
        EqualTo('password', message='两次输入的密码不一致')
    ])
    real_name = StringField('姓名', validators=[DataRequired(message='姓名不能为空')])
    student_id = StringField('学号', validators=[
        DataRequired(message='学号不能为空'),
        Length(min=5, max=20, message='请输入有效的学号')
    ])
    grade = StringField('年级', validators=[DataRequired(message='年级不能为空')])
    major = StringField('专业', validators=[DataRequired(message='专业不能为空')])
    college = StringField('学院', validators=[DataRequired(message='学院不能为空')])
    phone = StringField('手机号', validators=[
        DataRequired(message='手机号不能为空'),
        Regexp(r'^1[3-9][0-9]{9}$', message='请输入有效的手机号码')
    ])
    qq = StringField('QQ号', validators=[
        DataRequired(message='QQ号不能为空'),
        Regexp(r'^[0-9]{5,12}$', message='请输入有效的QQ号码')
    ])
    submit = SubmitField('注册')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('该用户名已被注册')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('该邮箱已被注册')
            
    def validate_student_id(self, field):
        if StudentInfo.query.filter_by(student_id=field.data).first():
            raise ValidationError('该学号已被注册')

# 登录表单
class LoginForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired(message='用户名不能为空')])
    password = PasswordField('密码', validators=[DataRequired(message='密码不能为空')])
    submit = SubmitField('登录')

# 管理员设置表单
class SetupAdminForm(FlaskForm):
    username = StringField('管理员用户名', validators=[
        DataRequired(message='用户名不能为空'),
        Length(min=3, max=20, message='用户名长度必须在3-20个字符之间'),
        Regexp('^[A-Za-z0-9_]*$', message='用户名只能包含字母、数字和下划线')
    ])
    email = StringField('管理员邮箱', validators=[
        DataRequired(message='邮箱不能为空'),
        Email(message='请输入有效的邮箱地址')
    ])
    password = PasswordField('密码', validators=[
        DataRequired(message='密码不能为空'),
        Length(min=6, message='密码长度不能少于6个字符')
    ])
    confirm_password = PasswordField('确认密码', validators=[
        DataRequired(message='确认密码不能为空'),
        EqualTo('password', message='两次输入的密码不一致')
    ])
    submit = SubmitField('创建管理员')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('该用户名已被注册')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('该邮箱已被注册')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # 获取学生角色
        student_role = Role.query.filter_by(name='Student').first()
        if not student_role:
            student_role = Role(name='Student')
            db.session.add(student_role)
            db.session.commit()
        
        # 创建用户
        user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=generate_password_hash(form.password.data),
            role=student_role
        )
        db.session.add(user)
        db.session.flush()  # 获取用户ID
        
        # 创建学生信息
        student_info = StudentInfo(
            user_id=user.id,
            real_name=form.real_name.data,
            student_id=form.student_id.data,
            grade=form.grade.data,
            major=form.major.data,
            college=form.college.data,
            phone=form.phone.data,
            qq=form.qq.data
        )
        db.session.add(student_info)
        
        # 创建AI用户偏好设置
        ai_preferences = AIUserPreferences(
            user_id=user.id,
            enable_history=True,
            max_history_count=50
        )
        db.session.add(ai_preferences)
        
        db.session.commit()
        
        flash('注册成功，请登录！', 'success')
        # 登录用户并重定向到标签选择页面
        login_user(user)
        return redirect(url_for('auth.select_tags'))
    
    return render_template('auth/register.html', form=form)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    form = LoginForm()
    
    # 如果是GET请求，直接显示登录表单
    if request.method == 'GET':
        return render_template('auth/login.html', form=form)
    
    # 如果是POST请求，处理表单提交
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        
        logger.info(f"尝试登录: 用户名={username}")
        
        try:
            # 查询用户
            user = User.query.filter_by(username=username).first()
            
            if user and user.check_password(password):
                # 登录成功
                login_user(user)
                
                # 更新最后登录时间
                user.last_login = datetime.now()
                db.session.commit()
                
                logger.info(f"用户 {username} 登录成功")
                
                # 记录系统日志
                log = SystemLog(
                    user_id=user.id,
                    action='登录',
                    details=f'用户 {username} 登录成功',
                    ip_address=request.remote_addr
                )
                db.session.add(log)
                db.session.commit()
                
                # 获取next参数，如果有的话重定向到该页面
                next_page = request.args.get('next')
                if not next_page or next_page.startswith('//'):
                    if hasattr(user, 'role') and user.role and user.role.name == 'Admin':
                        next_page = url_for('admin.dashboard')
                    else:
                        next_page = url_for('student.dashboard')
                
                flash('登录成功！', 'success')
                return redirect(next_page)
            else:
                # 登录失败
                logger.warning(f"用户 {username} 登录失败: 用户名或密码错误")
                flash('用户名或密码错误，请重试。', 'danger')
                return render_template('auth/login.html', form=form)
                
        except Exception as e:
            # 捕获所有异常，确保即使数据库查询失败也能正常显示错误信息
            logger.error(f"登录查询错误: {str(e)}")
            logger.error(f"登录过程发生错误: {str(e)}", exc_info=True)
            flash('登录过程中发生错误，请稍后再试。', 'danger')
            return render_template('auth/login.html', form=form)
    
    # 表单验证失败
    return render_template('auth/login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    """用户登出"""
    logout_user()
    flash('您已成功登出！', 'success')
    return redirect(url_for('main.index'))

@auth_bp.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html')

@auth_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    class ChangePasswordForm(FlaskForm):
        old_password = PasswordField('当前密码', validators=[DataRequired(message='当前密码不能为空')])
        new_password = PasswordField('新密码', validators=[
            DataRequired(message='新密码不能为空'),
            Length(min=6, message='密码长度不能少于6个字符')
        ])
        confirm_password = PasswordField('确认新密码', validators=[
            DataRequired(message='确认密码不能为空'),
            EqualTo('new_password', message='两次输入的密码不一致')
        ])
        submit = SubmitField('修改密码')
    
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if check_password_hash(current_user.password_hash, form.old_password.data):
            current_user.password_hash = generate_password_hash(form.new_password.data)
            db.session.commit()
            flash('密码修改成功！', 'success')
            return redirect(url_for('auth.profile'))
        else:
            flash('当前密码不正确', 'danger')
    
    return render_template('auth/change_password.html', form=form)

@auth_bp.route('/setup-admin', methods=['GET', 'POST'])
def setup_admin():
    # 检查是否已存在管理员账户
    admin_role = Role.query.filter_by(name='Admin').first()
    if admin_role and User.query.filter_by(role_id=admin_role.id).first():
        flash('管理员账户已存在，无法重复创建', 'warning')
        return redirect(url_for('main.index'))
    
    form = SetupAdminForm()
    if form.validate_on_submit():
        # 创建管理员角色（如果不存在）
        if not admin_role:
            admin_role = Role(name='Admin')
            db.session.add(admin_role)
            db.session.commit()
        
        # 创建管理员用户
        admin = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=generate_password_hash(form.password.data),
            role=admin_role
        )
        db.session.add(admin)
        db.session.flush()  # 获取用户ID
        
        # 创建AI用户偏好设置
        ai_preferences = AIUserPreferences(
            user_id=admin.id,
            enable_history=True,
            max_history_count=100  # 管理员可以存储更多历史记录
        )
        db.session.add(ai_preferences)
        
        db.session.commit()
        
        flash('管理员账户创建成功，请登录！', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/setup_admin.html', form=form)

@auth_bp.route('/select-tags', methods=['GET', 'POST'])
@login_required
def select_tags():
    # 只有学生用户可以选择标签
    if not current_user.role or current_user.role.name != 'Student':
        return redirect(url_for('main.index'))
    
    # 获取学生信息
    student_info = StudentInfo.query.filter_by(user_id=current_user.id).first()
    if not student_info:
        flash('未找到学生信息', 'danger')
        return redirect(url_for('main.index'))
    
    # 获取所有标签
    tags = Tag.query.all()
    
    # 获取已选标签ID
    selected_tag_ids = []
    for tag in student_info.tags:
        selected_tag_ids.append(tag.id)
    
    if request.method == 'POST':
        # 获取提交的标签ID
        tag_ids = request.form.getlist('tags')
        
        if not tag_ids:
            flash('请至少选择一个兴趣标签', 'warning')
            return render_template('select_tags.html', tags=tags, selected_tag_ids=selected_tag_ids)
        
        try:
            # 清除原有标签关联
            student_info.tags = []
            
            # 添加新的标签关联
            for tag_id in tag_ids:
                tag = Tag.query.get(int(tag_id))
                if tag:
                    student_info.tags.append(tag)
            
            # 更新学生标签选择状态
            student_info.has_selected_tags = True
            db.session.commit()
            
            flash('兴趣标签保存成功！', 'success')
            return redirect(url_for('student.dashboard'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"保存标签时出错: {e}")
            flash('保存标签时出错，请稍后再试', 'danger')
    
    return render_template('select_tags.html', tags=tags, selected_tag_ids=selected_tag_ids)
