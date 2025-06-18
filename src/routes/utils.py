from flask import Blueprint, redirect, url_for, flash, request, jsonify, abort
from flask_login import login_required, current_user
from functools import wraps
import logging
import os
import requests

utils_bp = Blueprint('utils', __name__)
logger = logging.getLogger(__name__)

# 初始化火山方舟客户端
client = Ark(
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    api_key="ccde7115-49bc-4977-9e17-e61075fa9eac",
)

# 管理员权限装饰器
def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        try:
            # 1. 验证用户认证状态
            if not current_user.is_authenticated:
                logger.warning(f"Unauthenticated access attempt to {request.path}")
                flash('请先登录', 'danger')
                return redirect(url_for('auth.login'))
            
            # 2. 验证用户对象完整性
            if not current_user or not hasattr(current_user, 'role_id'):
                logger.error(f"User object integrity error - user: {current_user}, path: {request.path}")
                flash('用户信息不完整', 'danger')
                return redirect(url_for('main.index'))

            # 3. 验证角色信息
            if not current_user.role_id:
                logger.error(f"User has no role_id - user: {current_user.username}, path: {request.path}")
                flash('未分配用户角色', 'danger')
                return redirect(url_for('main.index'))

            # 4. 验证角色对象
            if not current_user.role:
                logger.error(f"Role object not found - user: {current_user.username}, role_id: {current_user.role_id}, path: {request.path}")
                flash('角色信息不存在', 'danger')
                return redirect(url_for('main.index'))

            # 5. 验证角色名称
            role_name = getattr(current_user.role, 'name', '')
            if not role_name:
                logger.error(f"Role has no name - user: {current_user.username}, role: {current_user.role}, path: {request.path}")
                flash('角色名称未定义', 'danger')
                return redirect(url_for('main.index'))

            # 6. 验证管理员权限
            if role_name.lower() != 'admin':
                logger.warning(f"Non-admin access attempt - user: {current_user.username}, role: {role_name}, path: {request.path}")
                flash('您没有管理员权限', 'danger')
                return redirect(url_for('main.index'))

            # 权限验证通过
            logger.info(f"Admin access granted - user: {current_user.username}, path: {request.path}")
            return f(*args, **kwargs)

        except Exception as e:
            logger.error(f"Error in admin_required - user: {getattr(current_user, 'username', 'Unknown')}, "
                        f"path: {request.path}, error: {str(e)}")
            flash('权限验证时出错', 'danger')
            return redirect(url_for('main.index'))
    return decorated_function

# 学生权限装饰器
def student_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        try:
            if not getattr(current_user, 'is_authenticated', False):
                flash('请先登录', 'danger')
                return redirect(url_for('auth.login'))
            role = getattr(current_user, 'role', None)
            if not role or not getattr(role, 'name', None):
                flash('您没有权限访问此页面', 'danger')
                return redirect(url_for('main.index'))
            if str(role.name).lower() != 'student':
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

@utils_bp.route('/api/ai_chat', methods=['POST'])
def ai_chat():
    data = request.json
    user_message = data.get('message', '')
    user_role = data.get('role', 'student')  # 默认为学生端

    api_key = os.environ.get("ARK_API_KEY")
    url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "x-is-encrypted": "true"
    }
    if user_role == 'student':
        system_prompt = "你是一个智能助手，可以回答活动相关问题并推荐相关活动。"
    else:
        system_prompt = "你是一个智能助手，可以总结反馈信息。"
    payload = {
        "model": "doubao-seed-1.6",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "temperature": 1,
        "top_p": 0.7,
        "max_tokens": 4096,
        "frequency_penalty": 0
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        response = result["choices"][0]["message"]["content"]
        return jsonify({"response": response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
