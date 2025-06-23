from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
import pytz
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float, Table, func, UniqueConstraint
from sqlalchemy.orm import relationship, backref

# 从src/__init__.py导入db实例
from src import db

# 角色模型
class Role(db.Model):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True)
    name = Column(String(64), unique=True)
    description = Column(String(128))  # 新增，支持角色描述
    
    # 关系
    users = relationship('User', backref='role', lazy='dynamic')
    
    def __repr__(self):
        return f'<Role {self.name}>'

# 用户模型
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, index=True)
    email = Column(String(120), unique=True, index=True)
    password_hash = Column(String(256))  # 已修改：从128扩展到256
    role_id = Column(Integer, ForeignKey('roles.id'))
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    last_login = Column(DateTime)
    
    # 关系
    student_info = relationship('StudentInfo', backref='user', uselist=False)
    registrations = relationship('Registration', backref='user', lazy='dynamic')
    reviews = relationship('ActivityReview', backref='user', lazy='dynamic')
    points_history = relationship('PointsHistory', backref='user', lazy='dynamic')
    checkins = relationship('ActivityCheckin', backref='user', lazy='dynamic')
    sent_messages = relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy='dynamic')
    received_messages = relationship('Message', foreign_keys='Message.recipient_id', backref='recipient', lazy='dynamic')
    notifications = relationship('Notification', foreign_keys='Notification.user_id', backref='user', lazy='dynamic')
    read_notifications = relationship('NotificationRead', backref='user', lazy='dynamic')
    chat_histories = relationship('AIChatHistory', backref='user', lazy='dynamic')
    chat_sessions = relationship('AIChatSession', backref='user', lazy='dynamic')
    ai_preferences = relationship('AIUserPreferences', backref='user', uselist=False)
    
    def __repr__(self):
        return f'<User {self.username}>'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @property
    def is_admin(self):
        return self.role and self.role.name == 'Admin'
    
    @property
    def is_active(self):
        return self.active

# 学生信息模型
class StudentInfo(db.Model):
    __tablename__ = 'student_info'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True)
    real_name = Column(String(64))
    student_id = Column(String(20), unique=True, index=True)
    grade = Column(String(10))
    major = Column(String(64))
    college = Column(String(64))
    phone = Column(String(20))
    qq = Column(String(20))
    points = Column(Integer, default=0)  # 积分
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 多对多关系通过student_tags表
    tags = relationship('Tag', secondary='student_tags', backref=backref('students', lazy='dynamic'))
    
    def __repr__(self):
        return f'<StudentInfo {self.real_name}>'

# 标签模型
class Tag(db.Model):
    __tablename__ = 'tags'
    id = Column(Integer, primary_key=True)
    name = Column(String(64), unique=True)
    category = Column(String(64))  # 标签分类，如"兴趣"、"技能"等
    created_at = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        return f'<Tag {self.name}>'

# 学生-标签关联表
student_tags = db.Table('student_tags',
    Column('student_id', Integer, ForeignKey('student_info.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True)
)

# 活动-标签关联表
activity_tags = db.Table('activity_tags',
    Column('activity_id', Integer, ForeignKey('activities.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True)
)

# 活动模型
class Activity(db.Model):
    __tablename__ = 'activities'
    id = Column(Integer, primary_key=True)
    title = Column(String(128))
    description = Column(Text)
    location = Column(String(128))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    registration_deadline = Column(DateTime)
    max_participants = Column(Integer, default=0)  # 0表示不限制人数
    min_participants = Column(Integer, default=0)  # 最小参与人数，0表示不限制
    points = Column(Integer, default=0)  # 参与可获得的积分
    type = Column(String(64), default='general')  # 活动类型
    status = Column(String(20), default='draft')  # 状态：draft, active, cancelled, completed
    poster_url = Column(String(256))  # 海报URL
    created_by = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系
    creator = relationship('User', backref='created_activities')
    registrations = relationship('Registration', backref='activity', lazy='dynamic', cascade="all, delete-orphan")
    reviews = relationship('ActivityReview', backref='activity', lazy='dynamic', cascade="all, delete-orphan")
    checkins = relationship('ActivityCheckin', backref='activity', lazy='dynamic', cascade="all, delete-orphan")
    tags = relationship('Tag', secondary=activity_tags, backref=backref('activities', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Activity {self.title}>'
    
    def is_registrable(self):
        now = datetime.now()
        return (self.status == 'active' and 
                now <= self.registration_deadline and 
                (self.max_participants == 0 or 
                 self.registrations.count() < self.max_participants))
    
    def is_ongoing(self):
        now = datetime.now()
        return self.start_time <= now <= self.end_time and self.status == 'active'
    
    def is_past(self):
        return datetime.now() > self.end_time
    
    def is_upcoming(self):
        return datetime.now() < self.start_time

# 活动报名模型
class Registration(db.Model):
    __tablename__ = 'registrations'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    activity_id = Column(Integer, ForeignKey('activities.id'))
    status = Column(String(20), default='pending')  # pending, approved, rejected, cancelled
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f'<Registration {self.id}>'

# 积分历史模型
class PointsHistory(db.Model):
    __tablename__ = 'points_history'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    activity_id = Column(Integer, ForeignKey('activities.id'), nullable=True)
    points = Column(Integer)  # 正数为获得积分，负数为消费积分
    reason = Column(String(128))
    created_at = Column(DateTime, default=datetime.now)
    
    # 关系
    activity = relationship('Activity')
    
    def __repr__(self):
        return f'<PointsHistory {self.id}>'

# 活动评价模型
class ActivityReview(db.Model):
    __tablename__ = 'activity_reviews'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    activity_id = Column(Integer, ForeignKey('activities.id'))
    rating = Column(Integer)  # 1-5星评价
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f'<ActivityReview {self.id}>'

# 公告模型
class Announcement(db.Model):
    __tablename__ = 'announcements'
    id = Column(Integer, primary_key=True)
    title = Column(String(128))
    content = Column(Text)
    created_by = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系
    creator = relationship('User', backref='announcements')
    
    def __repr__(self):
        return f'<Announcement {self.title}>'

# 系统日志模型
class SystemLog(db.Model):
    __tablename__ = 'system_logs'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    action = Column(String(64))
    details = Column(Text)
    ip_address = Column(String(64))
    created_at = Column(DateTime, default=datetime.now)
    
    # 关系
    user = relationship('User', backref='logs')
    
    def __repr__(self):
        return f'<SystemLog {self.id}>'

# 活动签到模型
class ActivityCheckin(db.Model):
    __tablename__ = 'activity_checkins'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    activity_id = Column(Integer, ForeignKey('activities.id'))
    checkin_time = Column(DateTime, default=datetime.now)
    is_manual = Column(Boolean, default=False)  # 是否为管理员手动签到
    
    def __repr__(self):
        return f'<ActivityCheckin {self.id}>'

# 消息模型
class Message(db.Model):
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True)
    sender_id = Column(Integer, ForeignKey('users.id'))
    recipient_id = Column(Integer, ForeignKey('users.id'))
    subject = Column(String(128))
    content = Column(Text)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        return f'<Message {self.id}>'

# 通知模型
class Notification(db.Model):
    __tablename__ = 'notification'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)  # 为空表示系统通知
    title = Column(String(128))
    content = Column(Text)
    is_public = Column(Boolean, default=False)  # 是否为公开通知
    is_important = Column(Boolean, default=False)  # 是否为重要通知
    expiry_date = Column(DateTime, nullable=True)  # 过期时间，为空表示永不过期
    created_at = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        return f'<Notification {self.id}>'

# 通知已读模型
class NotificationRead(db.Model):
    __tablename__ = 'notification_read'
    
    id = Column(Integer, primary_key=True)
    notification_id = Column(Integer, ForeignKey('notification.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    read_at = Column(DateTime, default=datetime.now)
    
    # 唯一约束，确保一个用户只能标记一个通知为已读一次
    __table_args__ = (UniqueConstraint('notification_id', 'user_id', name='uq_notification_user'),)
    
    # 关系
    notification = relationship('Notification', backref='reads')
    
    def __repr__(self):
        return f'<NotificationRead {self.id}>'

# AI聊天历史模型
class AIChatHistory(db.Model):
    __tablename__ = 'ai_chat_history'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    session_id = Column(String(64), index=True)
    role = Column(String(20))  # 'user' 或 'assistant'
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        return f'<AIChatHistory {self.id}>'

# AI聊天会话模型
class AIChatSession(db.Model):
    __tablename__ = 'ai_chat_sessions'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    session_id = Column(String(64), unique=True, index=True)
    title = Column(String(128))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系
    messages = relationship('AIChatHistory', primaryjoin="and_(AIChatSession.session_id==AIChatHistory.session_id)", 
                           order_by="AIChatHistory.created_at", 
                           foreign_keys="AIChatHistory.session_id", 
                           viewonly=True)
    
    def __repr__(self):
        return f'<AIChatSession {self.session_id}>'

# AI用户偏好设置
class AIUserPreferences(db.Model):
    __tablename__ = 'ai_user_preferences'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True)
    enable_history = Column(Boolean, default=True)  # 是否保存聊天历史
    max_history_count = Column(Integer, default=50)  # 最大保存的聊天历史条数
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f'<AIUserPreferences {self.id}>'
