from flask import current_app, render_template
from flask_mail import Message
from src import mail
from threading import Thread
import logging

logger = logging.getLogger(__name__)

def send_async_email(app, msg):
    """异步发送邮件的后台任务"""
    with app.app_context():
        try:
            mail.send(msg)
            logger.info(f"邮件发送成功: {msg.subject} 发送至 {msg.recipients}")
        except Exception as e:
            logger.error(f"邮件发送失败: {str(e)}")

def send_email(to, subject, template, **kwargs):
    """发送邮件
    
    Args:
        to: 收件人邮箱地址
        subject: 邮件主题
        template: 邮件模板名称，不包含扩展名
        **kwargs: 传递给模板的参数
    """
    app = current_app._get_current_object()
    
    # 添加邮件主题前缀
    prefix = app.config.get('MAIL_SUBJECT_PREFIX', '')
    full_subject = f"{prefix}{subject}"
    
    # 创建邮件消息
    msg = Message(full_subject, recipients=[to])
    
    # 渲染邮件内容
    msg.body = render_template(f'email/{template}.txt', **kwargs)
    msg.html = render_template(f'email/{template}.html', **kwargs)
    
    # 异步发送邮件
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    
    return thr

def send_confirmation_email(user):
    """发送邮箱验证邮件
    
    Args:
        user: 用户对象，必须包含 email 和 confirmation_token 属性
    """
    # 生成验证链接
    token = user.generate_confirmation_token()
    
    # 发送验证邮件
    send_email(
        to=user.email,
        subject='请验证您的电子邮箱',
        template='confirm_email',
        user=user,
        token=token
    )
    
    return True 