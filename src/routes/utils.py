from flask import Blueprint, redirect, url_for, flash, request, jsonify, abort
from flask_login import login_required, current_user
from functools import wraps
import logging

utils_bp = Blueprint('utils', __name__)
logger = logging.getLogger(__name__)

# 管理员权限装饰器
def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        try:
            # 支持 admin/Admin 不区分大小写
            if not current_user.role or current_user.role.name.lower() != 'admin':
                flash('您没有权限访问此页面', 'danger')
                return redirect(url_for('main.index'))
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in admin_required: {e}")
            flash('权限验证时出错', 'danger')
            return redirect(url_for('main.index'))
    return decorated_function

# 学生权限装饰器
def student_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        try:
            if not current_user.role or current_user.role.name != 'Student':
                flash('您没有权限访问此页面', 'danger')
                return redirect(url_for('main.index'))
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in student_required: {e}")
            flash('权限验证时出错', 'danger')
            return redirect(url_for('main.index'))
    return decorated_function

# 添加缺失的log_action函数
def log_action(action, details=None, user_id=None):
    """记录系统操作日志
    
    Args:
        action: 操作类型
        details: 操作详情
        user_id: 用户ID，如果为None则使用当前登录用户ID
    """
    try:
        from src.models import SystemLog, db
        import datetime
        
        if user_id is None and current_user.is_authenticated:
            user_id = current_user.id
        
        log = SystemLog(
            user_id=user_id,
            action=action,
            details=details,
            ip_address=request.remote_addr,
            created_at=datetime.datetime.now()
        )
        
        db.session.add(log)
        db.session.commit()
        logger.info(f"Action logged: {action} by user {user_id}")
    except Exception as e:
        logger.error(f"Error logging action: {e}")
        db.session.rollback()

# API响应生成器
def api_response(success, message, data=None, status_code=200):
    response = {
        'success': success,
        'message': message
    }
    if data is not None:
        response['data'] = data
    return jsonify(response), status_code

# 活动签到API
@utils_bp.route('/api/activity/<int:activity_id>/check_in/<int:registration_id>', methods=['POST'])
@admin_required
def check_in(activity_id, registration_id):
    from src.models import Registration, db
    try:
        registration = Registration.query.get_or_404(registration_id)
        
        # 确认是否为指定活动的报名
        if registration.activity_id != activity_id:
            return api_response(False, '报名信息与活动不匹配', status_code=400)
        
        # 更新状态为已参加
        registration.status = 'attended'
        db.session.commit()
        
        # 记录操作日志
        log_action('check_in', f'签到活动 {activity_id} 的报名 {registration_id}')
        
        return api_response(True, '签到成功')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in check_in: {e}")
        return api_response(False, f'签到失败: {str(e)}', status_code=500)

# 取消报名API
@utils_bp.route('/api/activity/<int:activity_id>/cancel/<int:registration_id>', methods=['POST'])
@admin_required
def cancel_registration(activity_id, registration_id):
    from src.models import Registration, db
    try:
        registration = Registration.query.get_or_404(registration_id)
        
        # 确认是否为指定活动的报名
        if registration.activity_id != activity_id:
            return api_response(False, '报名信息与活动不匹配', status_code=400)
        
        # 更新状态为已取消
        registration.status = 'cancelled'
        db.session.commit()
        
        # 记录操作日志
        log_action('cancel_registration', f'取消活动 {activity_id} 的报名 {registration_id}')
        
        return api_response(True, '已取消报名')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in cancel_registration: {e}")
        return api_response(False, f'取消报名失败: {str(e)}', status_code=500)
