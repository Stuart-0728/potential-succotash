# 工具函数包 
import json
import uuid
from datetime import datetime
from flask import current_app

def generate_session_id():
    """生成唯一的会话ID"""
    timestamp = int(datetime.now().timestamp() * 1000)
    random_str = uuid.uuid4().hex[:12]
    return f"session_{timestamp}_{random_str}"

def create_ai_chat_session(db, user_id):
    """创建新的AI聊天会话"""
    from src.models import AIChatSession
    
    session_id = generate_session_id()
    session = AIChatSession(
        id=session_id,
        user_id=user_id
    )
    
    try:
        db.session.add(session)
        db.session.commit()
        return session
    except Exception as e:
        current_app.logger.error(f"创建AI聊天会话失败: {str(e)}")
        db.session.rollback()
        return None

def save_chat_message(db, user_id, session_id, role, content):
    """保存聊天消息到数据库"""
    from src.models import AIChatHistory
    
    try:
        message = AIChatHistory(
            user_id=user_id,
            session_id=session_id,
            role=role,
            content=content
        )
        db.session.add(message)
        db.session.commit()
        return message
    except Exception as e:
        current_app.logger.error(f"保存聊天消息失败: {str(e)}")
        db.session.rollback()
        return None 