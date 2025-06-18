from flask import Blueprint, redirect, url_for, flash, request, jsonify, abort, Response
from flask_login import login_required, current_user
from functools import wraps
import logging
import os
import requests
import uuid
import json
from src.models import Activity, Tag, StudentInfo

utils_bp = Blueprint('utils', __name__)
logger = logging.getLogger(__name__)

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

def get_interest_activities(user_id, limit=10):
    student_info = StudentInfo.query.filter_by(user_id=user_id).first()
    if not student_info or not student_info.tags:
        # 没有兴趣标签则返回最新活动
        return Activity.query.order_by(Activity.created_at.desc()).limit(limit).all()
    tag_ids = [tag.id for tag in student_info.tags]
    activities = Activity.query.join(Activity.tags).filter(Tag.id.in_(tag_ids)).order_by(Activity.created_at.desc()).distinct().limit(limit).all()
    return activities

def build_activity_context(activities):
    if not activities:
        return "当前暂无可推荐的活动。"
    return "\n".join([f"{a.title}：{a.description[:40]}..." for a in activities])

@utils_bp.route('/api/ai_chat', methods=['GET'])
def ai_chat():
    if not current_user.is_authenticated:
        return jsonify({'error': 'AI功能需要登录使用'}), 401
    user_message = request.args.get('message', '')
    user_role = request.args.get('role', 'student')

    api_key = os.environ.get("ARK_API_KEY")
    if not api_key:
        logger.error("ARK_API_KEY 环境变量未设置")
        return jsonify({
            'success': False,
            'error': 'AI 服务配置错误：API 密钥未设置'
        }), 500

    url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "X-Request-Id": str(uuid.uuid4())
    }

    # 获取用户信息
    student_info = StudentInfo.query.filter_by(user_id=current_user.id).first()
    user_tags = [tag.name for tag in student_info.tags] if student_info and student_info.tags else []
    
    # 获取用户参与的活动
    from src.models import Registration
    participated_activities = Activity.query.join(
        Registration, Activity.id == Registration.activity_id
    ).filter(
        Registration.user_id == current_user.id
    ).all()
    
    # 获取活跃的活动
    active_activities = Activity.query.filter_by(status='active').order_by(Activity.created_at.desc()).limit(5).all()
    
    # 构建上下文信息
    user_context = f"""
用户信息：
- 用户名：{current_user.username}
- 兴趣标签：{', '.join(user_tags) if user_tags else '暂无'}
- 已参与活动：{len(participated_activities)}个

最近活动：
{chr(10).join([f'- {a.title}' for a in active_activities[:5]]) if active_activities else '- 暂无活动'}
"""

    if user_role == 'student':
        system_prompt = f"""你是一个智能助手，可以访问以下信息：
{user_context}

你可以：
1. 根据用户兴趣标签推荐相关活动
2. 回答用户关于活动的问题
3. 提供活动参与建议
4. 分析用户参与历史

请根据用户的问题，结合上述信息提供个性化的回答。
重要：不要假设用户正在查看某个特定活动，除非用户明确提及。
"""
    else:
        system_prompt = "你是一个智能助手，可以总结反馈信息。你可以：1. 分析活动反馈 2. 总结用户建议 3. 提供改进意见"

    payload = {
        "model": "deepseek-r1-distill-qwen-7b-250120",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.7,
        "stream": True
    }

    def generate():
        try:
            logger.info(f"发送 AI 请求: URL={url}, Headers={headers}, Payload={payload}")
            response = requests.post(url, headers=headers, json=payload, timeout=30, stream=True)
            logger.info(f"AI API 响应状态码: {response.status_code}")
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]  # 去掉 'data: ' 前缀
                        if data == '[DONE]':
                            break
                        try:
                            chunk = json.loads(data)
                            if 'choices' in chunk and len(chunk['choices']) > 0:
                                content = chunk['choices'][0].get('delta', {}).get('content', '')
                                if content:
                                    yield f"data: {json.dumps({'content': content})}\n\n"
                        except json.JSONDecodeError:
                            continue
        except requests.exceptions.RequestException as e:
            logger.error(f"AI API 调用失败: {str(e)}")
            yield f"data: {json.dumps({'error': 'AI 服务调用失败'})}\n\n"
        except Exception as e:
            logger.error(f"处理 AI 响应时出错: {str(e)}")
            yield f"data: {json.dumps({'error': '处理 AI 响应时出错'})}\n\n"

    return Response(generate(), mimetype='text/event-stream')
