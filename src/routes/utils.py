from flask import Blueprint, redirect, url_for, flash, request, jsonify, abort, Response, render_template, current_app
from flask_login import login_required, current_user
from functools import wraps
import logging
import os
import requests
import uuid
import json
import random
import string
from datetime import datetime, timedelta
from sqlalchemy import func
from src.models import db, Activity, Tag, StudentInfo, SystemLog, Registration, AIChatHistory, AIChatSession, activity_tags, PointsHistory, User, Role, Message
from src.utils.time_helpers import get_beijing_time, ensure_timezone_aware

utils_bp = Blueprint('utils', __name__)
logger = logging.getLogger(__name__)

# 管理员权限装饰器
def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        try:
            # 验证用户是否为管理员
            if not current_user.is_authenticated:
                logger.warning(f"未认证的访问尝试: {request.path}")
                flash('请先登录', 'danger')
                return redirect(url_for('auth.login'))
            
            # 检查用户角色
            if not hasattr(current_user, 'role') or not current_user.role:
                logger.error(f"用户没有角色: {current_user.username}")
                flash('您没有被分配角色', 'danger')
                return redirect(url_for('main.index'))
            
            # 检查角色名称
            if not hasattr(current_user.role, 'name') or current_user.role.name.lower() != 'admin':
                # 特殊情况：允许所有用户访问/activities路由
                if request.path == '/activities' or request.path.startswith('/activities/'):
                    return f(*args, **kwargs)
                
                logger.warning(f"非管理员访问尝试: {current_user.username}, 路径: {request.path}")
                flash('您没有管理员权限', 'danger')
                return redirect(url_for('main.index'))
            
            # 权限验证通过
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"admin_required装饰器错误: {str(e)}")
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
        from src.utils.time_helpers import ensure_timezone_aware
        
        if user_id is None and current_user.is_authenticated:
            user_id = current_user.id
        
        log = SystemLog(
            user_id=user_id,
            action=action,
            details=details,
            ip_address=request.remote_addr,
            created_at=ensure_timezone_aware(datetime.datetime.now())
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
        registration = db.get_or_404(Registration, registration_id)
        
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
        registration = db.get_or_404(Registration, registration_id)
        
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
    student_info = db.session.execute(db.select(StudentInfo).filter_by(user_id=user_id)).scalar_one_or_none()
    if not student_info or not student_info.tags:
        # 没有兴趣标签则返回最新活动
        return db.session.execute(db.select(Activity).order_by(Activity.created_at.desc()).limit(limit)).scalars().all()
    
    tag_ids = [tag.id for tag in student_info.tags]
    
    # 使用SQLAlchemy 2.0风格查询
    activities_stmt = db.select(Activity).join(
        activity_tags, Activity.id == activity_tags.c.activity_id
    ).join(
        Tag, Tag.id == activity_tags.c.tag_id
    ).filter(
        Tag.id.in_(tag_ids)
    ).order_by(Activity.created_at.desc()).distinct().limit(limit)
    
    activities = db.session.execute(activities_stmt).scalars().all()
    return activities

def build_activity_context(activities):
    if not activities:
        return "当前暂无可推荐的活动。"
    return "\n".join([f"{a.title}：{a.description[:40]}..." for a in activities])

# 独立的AI聊天API路由 - 添加到utils_bp蓝图
@utils_bp.route('/utils/ai_chat/api', methods=['GET'])
def utils_ai_chat_api():
    """提供AI聊天API，转发到ai_chat函数"""
    return ai_chat()

# 现有的AI聊天路由
@utils_bp.route('/api/ai_chat', methods=['GET'])
def ai_chat():
    if not current_user.is_authenticated:
        return jsonify({'error': 'AI功能需要登录使用'}), 401
    
    # 获取请求参数
    user_message = request.args.get('message', '')
    session_id = request.args.get('session_id', '')

    # 验证API密钥
    api_key = os.environ.get("ARK_API_KEY")
    if not api_key:
        # 尝试从应用配置获取API密钥
        api_key = current_app.config.get('VOLCANO_API_KEY')
        if not api_key:
            logger.error("未找到API密钥，既没有ARK_API_KEY环境变量，也没有VOLCANO_API_KEY配置")
            return jsonify({
                'success': False,
                'error': 'AI 服务配置错误：API 密钥未设置'
            }), 500

    # 获取API端点URL - 使用火山引擎官方提供的URL
    url = current_app.config.get('VOLCANO_API_URL', "https://ark.cn-beijing.volces.com/api/v3/chat/completions")
    logger.info(f"使用AI聊天API端点: {url}")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # 获取用户信息
    student_info = None
    if hasattr(current_user, 'student_info'):
        student_info = current_user.student_info

    # 确定用户角色
    is_admin = False
    if hasattr(current_user, 'role') and current_user.role:
        is_admin = current_user.role.name == 'Admin'

    # 构建用户上下文信息
    user_context = ""
    if student_info:  # 学生用户
        # 获取学生标签
        user_tags = [tag.name for tag in student_info.tags] if student_info.tags else []
        
        # 获取用户参与的活动
        participated_activities = Activity.query.join(
            Registration, Activity.id == Registration.activity_id
        ).filter(
            Registration.user_id == current_user.id
        ).all()
        
        # 获取活跃的活动
        active_activities = Activity.query.filter_by(status='active').order_by(Activity.created_at.desc()).limit(5).all()
        
        user_context = f"""
用户角色：学生
用户信息：
- 用户名：{current_user.username}
- 姓名：{student_info.real_name if student_info.real_name else '未设置'}
- 学院：{student_info.college if student_info.college else '未设置'}
- 专业：{student_info.major if student_info.major else '未设置'}
- 兴趣标签：{', '.join(user_tags) if user_tags else '暂无'}
- 已参与活动：{len(participated_activities)}个
- 积分：{student_info.points or 0}分

最近活动：
{chr(10).join([f'- {a.title} ({a.start_time.strftime("%Y-%m-%d")})' for a in active_activities[:5]]) if active_activities else '- 暂无活动'}
"""
    else:  # 管理员用户
        # 获取统计数据
        total_activities = db.session.execute(db.select(func.count()).select_from(Activity)).scalar()
        active_activities = db.session.execute(db.select(func.count()).select_from(Activity).filter_by(status='active')).scalar()
        completed_activities = db.session.execute(db.select(func.count()).select_from(Activity).filter_by(status='completed')).scalar()
        total_students = db.session.execute(db.select(func.count()).select_from(StudentInfo)).scalar()
        total_registrations = db.session.execute(db.select(func.count()).select_from(Registration)).scalar()
        attended_registrations = db.session.execute(db.select(func.count()).select_from(Registration).filter_by(status='checked_in')).scalar()
        
        # 获取活动参与度
        if total_registrations > 0:
            attendance_rate = f"{(attended_registrations / total_registrations) * 100:.1f}%"
        else:
            attendance_rate = "0%"
        
        # 最受欢迎的活动标签
        popular_tags = db.session.query(
            Tag.name, db.func.count(activity_tags.c.activity_id).label('count')
        ).join(activity_tags).group_by(Tag.id).order_by(db.text('count DESC')).limit(5).all()
        
        user_context = f"""
用户角色：管理员
平台统计数据：
- 总活动数：{total_activities}个
- 进行中活动：{active_activities}个
- 已结束活动：{completed_activities}个
- 注册学生数：{total_students}人
- 总报名人次：{total_registrations}次
- 实际参与人次：{attended_registrations}次
- 活动参与率：{attendance_rate}

热门标签：
{chr(10).join([f'- {tag[0]}: {tag[1]}次使用' for tag in popular_tags]) if popular_tags else '- 暂无数据'}
"""

    # 获取历史消息
    messages = []
    
    # 如果有会话ID，尝试获取该会话的历史消息
    if session_id:
        try:
            # 检查会话是否存在，如果不存在则创建
            session = db.session.get(AIChatSession, session_id)
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
    if is_admin:
        system_prompt = f"""您好，我是基于DeepSeek大语言模型的智能助手，为重庆师范大学师能素质协会平台的管理员提供服务。

我使用的是DeepSeek-r1-distill-qwen-7b-250120模型，可以为您这位管理员提供以下帮助：
1. 分析活动参与数据和学生参与情况
2. 提供平台用户活跃度和活动参与度分析
3. 根据标签数据提供活动规划建议
4. 协助管理员工作，提供数据洞察
5. 生成数据摘要和报告

我可以访问以下信息：
{user_context}

您可以询问我关于平台数据的分析、学生参与情况、活动建议等方面的问题。
"""
    else:
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

    # 添加系统消息
    messages.insert(0, {"role": "system", "content": system_prompt})
    
    # 添加用户当前消息
    messages.append({"role": "user", "content": user_message})

    # 构建API请求
    payload = {
        "model": "deepseek-v3-250324",  # 使用官方指定的模型
        "messages": messages,
        "temperature": 0.7,
        "stream": True
    }

    # 保存当前用户ID和会话ID，以便在流式响应中使用
    current_user_id = current_user.id if current_user.is_authenticated else None
    current_message = user_message
    current_session_id = session_id
    
    # 获取Flask应用实例的引用，避免上下文问题
    app = current_app._get_current_object()  # 获取实际的应用对象而不是代理

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
                try:
                    # 创建一个新的请求上下文
                    with app.app_context():
                        # 检查会话是否存在
                        session = db.session.execute(db.select(AIChatSession).filter_by(id=current_session_id)).scalar_one_or_none()
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
                        logger.info(f"已保存聊天历史记录，会话ID: {current_session_id}")
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

# 添加与前端对应的新路由
@utils_bp.route('/api/ai_chat', methods=['GET'], endpoint='api_ai_chat')
def api_ai_chat():
    return ai_chat()

# 添加utils前缀的API路由
@utils_bp.route('/api/ai_chat', methods=['GET'], endpoint='utils_api_ai_chat')
def utils_api_ai_chat():
    return ai_chat()

@utils_bp.route('/ai_chat/history', methods=['GET'])
@login_required
def ai_chat_history_endpoint():
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
        history_messages = db.session.execute(db.select(AIChatHistory).filter_by(
            session_id=session_id,
            user_id=current_user.id
        ).order_by(AIChatHistory.timestamp)).scalars().all()
        
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

# 添加utils前缀路由
@utils_bp.route('/utils/ai_chat/history', methods=['GET'])
@login_required
def utils_ai_chat_history():
    """获取AI聊天历史记录 - 带utils前缀的版本"""
    return ai_chat_history_endpoint()

@utils_bp.route('/ai_chat/clear', methods=['POST'])
@login_required
def ai_chat_clear():
    """清除指定会话的AI聊天历史记录"""
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({
            'success': False,
            'message': '缺少会话ID参数'
        }), 400
    
    try:
        # 删除历史记录
        db.session.execute(db.delete(AIChatHistory).filter_by(
            session_id=session_id,
            user_id=current_user.id
        ))
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '成功清除历史记录'
        })
    except Exception as e:
        logger.error(f"清除AI聊天历史记录失败: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'清除历史记录失败: {str(e)}'
        }), 500

# 添加utils前缀路由
@utils_bp.route('/utils/ai_chat/clear', methods=['POST'])
@login_required
def utils_ai_chat_clear():
    """清除指定会话的AI聊天历史记录 - 带utils前缀的版本"""
    return ai_chat_clear()

@utils_bp.route('/ai_chat/clear_history', methods=['POST'])
@login_required
def ai_chat_clear_history():
    """清除用户所有AI聊天历史记录"""
    try:
        # 删除用户的所有聊天记录
        sessions = db.session.execute(db.select(AIChatSession).filter_by(
            user_id=current_user.id
        )).scalars().all()
        
        for session in sessions:
            db.session.execute(db.delete(AIChatHistory).filter_by(
                session_id=session.id
            ))
        
        # 也可以选择删除会话本身
        db.session.execute(db.delete(AIChatSession).filter_by(
            user_id=current_user.id
        ))
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '成功清除所有历史记录'
        })
    except Exception as e:
        logger.error(f"清除所有AI聊天历史记录失败: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'清除所有历史记录失败: {str(e)}'
        }), 500

# 添加utils前缀路由
@utils_bp.route('/utils/ai_chat/clear_history', methods=['POST'])
@login_required
def utils_ai_chat_clear_history():
    """清除用户所有AI聊天历史记录 - 带utils前缀的版本"""
    return ai_chat_clear_history()

# 添加缺失的add_points函数
def add_points(user_id, points, reason, activity_id=None):
    """给学生添加积分并记录积分历史
    
    Args:
        user_id: 学生用户ID
        points: 积分数量，可以是正数（增加）或负数（减少）
        reason: 积分变动原因
        activity_id: 相关活动ID（可选）
    
    Returns:
        bool: 操作是否成功
    """
    try:
        # 避免循环导入
        from src.models import StudentInfo, PointsHistory
        
        # 查找学生信息
        student_info = db.session.execute(db.select(StudentInfo).filter_by(user_id=user_id)).scalar_one_or_none()
        if not student_info:
            logger.error(f"添加积分失败: 找不到用户ID为 {user_id} 的学生信息")
            return False
        
        # 更新学生积分
        student_info.points = (student_info.points or 0) + points
        
        # 创建积分历史记录
        history = PointsHistory(
            user_id=user_id,
            points_change=points,
            reason=reason,
            activity_id=activity_id,
            created_at=ensure_timezone_aware(datetime.now())
        )
        
        # 保存更改
        db.session.add(history)
        db.session.commit()
        
        logger.info(f"已为用户 {user_id} 添加 {points} 积分，原因: {reason}")
        return True
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"添加积分时出错: {str(e)}")
        return False

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

@utils_bp.route('/check_login_status')
def check_login_status():
    """检查用户登录状态"""
    is_logged_in = current_user.is_authenticated
    response_data = {
        'is_logged_in': is_logged_in,
        'user_id': current_user.id if is_logged_in else None,
        'username': current_user.username if is_logged_in else None
    }
    
    # 添加更多详细信息，帮助客户端处理
    if is_logged_in:
        response_data['role'] = current_user.role.name if hasattr(current_user, 'role') and current_user.role else None
        response_data['login_url'] = None
    else:
        response_data['login_url'] = url_for('auth.login')
    
    return jsonify(response_data)
