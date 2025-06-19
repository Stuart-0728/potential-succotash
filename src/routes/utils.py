from flask import Blueprint, redirect, url_for, flash, request, jsonify, abort, Response
from flask_login import login_required, current_user
from functools import wraps
import logging
import os
import requests
import uuid
import json
import random
import string
from datetime import datetime
from src.models import db, Activity, Tag, StudentInfo, SystemLog, Registration, AIChatHistory, AIChatSession

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
    
    # 获取请求参数
    user_message = request.args.get('message', '')
    user_role = request.args.get('role', 'student')
    session_id = request.args.get('session_id', '')
    
    # 验证API密钥
    api_key = os.environ.get("ARK_API_KEY")
    if not api_key:
        logger.error("ARK_API_KEY 环境变量未设置")
        return jsonify({
            'success': False,
            'error': 'AI 服务配置错误：API 密钥未设置'
        }), 500

    # API端点
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
    participated_activities = Activity.query.join(
        Registration, Activity.id == Registration.activity_id
    ).filter(
        Registration.user_id == current_user.id
    ).all()
    
    # 获取活跃的活动
    active_activities = Activity.query.filter_by(status='active').order_by(Activity.created_at.desc()).limit(5).all()
    
    # 构建用户上下文信息
    user_context = f"""
用户信息：
- 用户名：{current_user.username}
- 兴趣标签：{', '.join(user_tags) if user_tags else '暂无'}
- 已参与活动：{len(participated_activities)}个

最近活动：
{chr(10).join([f'- {a.title}' for a in active_activities[:5]]) if active_activities else '- 暂无活动'}
"""

    # 获取历史消息
    messages = []
    
    # 如果有会话ID，尝试获取该会话的历史消息
    if session_id:
        try:
            # 检查会话是否存在，如果不存在则创建
            session = AIChatSession.query.get(session_id)
            if not session:
                session = AIChatSession(id=session_id, user_id=current_user.id)
                db.session.add(session)
                db.session.commit()
            
            # 获取该会话的历史消息
            history_messages = AIChatHistory.query.filter_by(
                session_id=session_id
            ).order_by(AIChatHistory.timestamp).limit(20).all()
            
            # 将历史消息添加到messages列表
            for msg in history_messages:
                messages.append({"role": msg.role, "content": msg.content})
        except Exception as e:
            logger.error(f"获取聊天历史记录失败: {str(e)}")
    
    # 如果没有历史消息，初始化messages列表
    if not messages:
        messages = []
    
    # 系统提示词
    if user_role == 'student':
        system_prompt = f"""您好，我是基于DeepSeek大语言模型的智能助手，为重庆师范大学师能素质协会平台提供服务。

我使用的是DeepSeek-r1-distill-qwen-7b-250120模型，可以为您提供以下帮助：
1. 回答关于活动的问题
2. 根据您的兴趣标签推荐相关活动
3. 提供活动参与建议和报名流程指导
4. 分析您的参与历史和积分情况
5. 提供平台使用帮助

我可以访问以下信息：
{user_context}

如果我无法回答您的某些问题，您可以联系平台管理员(2023051101095@stu.cqnu.edu.cn)获取更详细的帮助。

请告诉我您需要什么帮助？
"""
    else:
        system_prompt = """你是一个基于DeepSeek大语言模型的智能助手，可以帮助管理员处理活动和学生信息。你可以：
1. 分析活动反馈和参与数据
2. 总结用户建议和评价
3. 提供平台改进意见
4. 协助管理员工作

如有问题，可以建议联系平台管理员邮箱：2023051101095@stu.cqnu.edu.cn"""

    # 添加系统消息
    messages.insert(0, {"role": "system", "content": system_prompt})
    
    # 添加用户当前消息
    messages.append({"role": "user", "content": user_message})

    # 构建API请求
    payload = {
        "model": "deepseek-r1-distill-qwen-7b-250120",
        "messages": messages,
        "temperature": 0.7,
        "stream": True
    }

    # 保存当前用户ID和会话ID，以便在流式响应中使用
    current_user_id = current_user.id if current_user.is_authenticated else None
    current_message = user_message
    current_session_id = session_id
    
    # 获取Flask应用实例的引用，避免上下文问题
    from flask import current_app
    app = current_app._get_current_object()

    def generate():
        nonlocal current_user_id, current_message, current_session_id
        try:
            logger.info(f"发送 AI 请求: URL={url}, Headers={headers}, Payload={payload}")
            response = requests.post(url, headers=headers, json=payload, timeout=30, stream=True)
            logger.info(f"AI API 响应状态码: {response.status_code}")
            response.raise_for_status()
            
            full_response = ""
            
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
                                    full_response += content
                                    yield f"data: {json.dumps({'content': content})}\n\n"
                        except json.JSONDecodeError:
                            continue
            
            # 响应结束，保存历史记录
            if current_session_id and full_response and current_user_id:
                # 使用应用上下文确保数据库操作在正确的上下文中执行
                with app.app_context():
                    try:
                        # 在请求上下文中保存聊天记录
                        # 检查会话是否存在
                        session = AIChatSession.query.filter_by(id=current_session_id).first()
                        if not session:
                            # 如果会话不存在，创建新会话
                            session = AIChatSession(id=current_session_id, user_id=current_user_id)
                            db.session.add(session)
                            db.session.commit()
                        
                        # 保存用户消息
                        user_history = AIChatHistory(
                            user_id=current_user_id,
                            session_id=current_session_id,
                            role="user",
                            content=current_message
                        )
                        db.session.add(user_history)
                        
                        # 保存AI回复
                        ai_history = AIChatHistory(
                            user_id=current_user_id,
                            session_id=current_session_id,
                            role="assistant",
                            content=full_response
                        )
                        db.session.add(ai_history)
                        
                        # 更新会话最后更新时间
                        session.updated_at = datetime.now()
                        db.session.commit()
                        
                    except Exception as e:
                        logger.error(f"保存聊天历史记录失败: {str(e)}")
                        db.session.rollback()
                    
            # 发送结束事件
            yield f"event: done\ndata: {{}}\n\n"
                    
        except requests.exceptions.RequestException as e:
            logger.error(f"AI API 调用失败: {str(e)}")
            yield f"data: {json.dumps({'error': 'AI 服务调用失败'})}\n\n"
        except Exception as e:
            logger.error(f"处理 AI 响应时出错: {str(e)}")
            yield f"data: {json.dumps({'error': '处理 AI 响应时出错'})}\n\n"

    return Response(generate(), mimetype='text/event-stream')

# AI聊天历史记录API
@utils_bp.route('/api/ai_chat/history', methods=['GET'])
@login_required
def ai_chat_history():
    """获取AI聊天历史记录"""
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({
            'success': False,
            'message': '缺少会话ID参数',
            'data': []
        }), 400
    
    try:
        # 查询历史记录
        history_messages = AIChatHistory.query.filter_by(
            session_id=session_id,
            user_id=current_user.id
        ).order_by(AIChatHistory.timestamp).all()
        
        # 格式化消息
        messages = [
            {
                'role': msg.role,
                'content': msg.content,
                'timestamp': msg.timestamp.isoformat()
            }
            for msg in history_messages
        ]
        
        return jsonify({
            'success': True,
            'message': '成功获取历史记录',
            'data': messages
        })
    except Exception as e:
        logger.error(f"获取AI聊天历史记录失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取历史记录失败: {str(e)}',
            'data': []
        }), 500

@utils_bp.route('/api/ai_chat/clear', methods=['POST'])
@login_required
def ai_chat_clear_history():
    """清除AI聊天历史记录"""
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({
            'success': False,
            'message': '缺少会话ID参数'
        }), 400
    
    try:
        # 查询该会话是否属于当前用户
        session = AIChatSession.query.filter_by(
            id=session_id,
            user_id=current_user.id
        ).first()
        
        if not session:
            return jsonify({
                'success': False,
                'message': '会话不存在或无权限清除'
            }), 403
        
        # 删除历史记录
        AIChatHistory.query.filter_by(
            session_id=session_id,
            user_id=current_user.id
        ).delete()
        
        # 提交更改
        db.session.commit()
        
        # 记录操作日志
        log_action(
            action='clear_ai_chat_history',
            details=f'清除AI聊天历史记录，会话ID: {session_id}'
        )
        
        return jsonify({
            'success': True,
            'message': '成功清除历史记录'
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"清除AI聊天历史记录失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'清除历史记录失败: {str(e)}'
        }), 500

@utils_bp.route('/api/ai_chat/clear_history', methods=['POST'])
@login_required
def ai_chat_clear_all_history():
    """清除用户所有AI聊天历史记录"""
    try:
        # 查询用户的所有会话
        sessions = AIChatSession.query.filter_by(
            user_id=current_user.id
        ).all()
        
        # 记录会话数量用于日志
        session_count = len(sessions)
        
        # 删除用户的所有历史记录
        deleted_count = AIChatHistory.query.filter_by(
            user_id=current_user.id
        ).delete()
        
        # 提交更改
        db.session.commit()
        
        # 记录操作日志
        log_action(
            action='clear_all_ai_chat_history',
            details=f'清除所有AI聊天历史记录，共删除{deleted_count}条记录，涉及{session_count}个会话'
        )
        
        return jsonify({
            'success': True,
            'message': f'成功清除所有历史记录，共{deleted_count}条',
            'deleted_count': deleted_count
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"清除所有AI聊天历史记录失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'清除历史记录失败: {str(e)}'
        }), 500

# 添加random_string函数
def random_string(length=6):
    """生成指定长度的随机字符串
    
    Args:
        length: 字符串长度，默认为6
    
    Returns:
        随机字符串
    """
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))
