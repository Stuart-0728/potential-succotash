from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
from ..utils.time_helpers import get_beijing_time, normalize_datetime_for_db
import pytz
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float, Table, func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

db = SQLAlchemy()

# 用户与角色关系表
roles_users = db.Table('roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('users.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('roles.id'))
)

# 学生与标签关系表
student_tags = db.Table('student_tags',
    db.Column('student_id', db.Integer(), db.ForeignKey('student_info.id')),
    db.Column('tag_id', db.Integer(), db.ForeignKey('tags.id'))
)

# 活动与标签关系表
activity_tags = db.Table('activity_tags',
    db.Column('activity_id', db.Integer(), db.ForeignKey('activities.id')),
    db.Column('tag_id', db.Integer(), db.ForeignKey('tags.id'))
)

# 角色模型
class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    description = db.Column(db.String(128))  # 新增，支持角色描述
    users = db.relationship('User', backref=db.backref('role', lazy='joined'), lazy='dynamic')

    def __repr__(self):
        return f'<Role {self.name}>'

# 用户模型
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    email = db.Column(db.String(120), unique=True, index=True)
    password_hash = db.Column(db.String(256))  # 已修改：从128扩展到256
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    active = db.Column(db.Boolean, default=True)
    student_info = db.relationship('StudentInfo', backref='user', uselist=False)
    registrations = db.relationship('Registration', backref='user', lazy='dynamic')
    created_at = db.Column(db.DateTime, default=lambda: normalize_datetime_for_db(datetime.now()))
    last_login = db.Column(db.DateTime)
    
    # AI聊天关联
    ai_chat_histories = db.relationship('AIChatHistory', backref='user', lazy='dynamic')
    ai_chat_sessions = db.relationship('AIChatSession', backref='user', lazy='dynamic')
    ai_preferences = db.relationship('AIUserPreferences', backref='user', uselist=False)

    def __repr__(self):
        return f'<User {self.username}>'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# 学生信息模型
class StudentInfo(db.Model):
    __tablename__ = 'student_info'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True)
    student_id = db.Column(db.String(20), unique=True)
    real_name = db.Column(db.String(50))
    gender = db.Column(db.String(10))
    grade = db.Column(db.String(20))
    college = db.Column(db.String(100))
    major = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    qq = db.Column(db.String(20))
    points = db.Column(db.Integer, default=0)
    points_history = db.relationship('PointsHistory', backref='student', lazy='dynamic')
    has_selected_tags = db.Column(db.Boolean, default=False)  # 新增字段
    tags = db.relationship('Tag', secondary=student_tags, backref=db.backref('students', lazy='dynamic'))  # 多对多

    def __repr__(self):
        return f'<StudentInfo {self.real_name}>'

# 积分变更历史表
class PointsHistory(db.Model):
    __tablename__ = 'points_history'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student_info.id'))
    points = db.Column(db.Integer)
    reason = db.Column(db.String(200))
    activity_id = db.Column(db.Integer, db.ForeignKey('activities.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: normalize_datetime_for_db(datetime.now()))

# 活动模型
class Activity(db.Model):
    __tablename__ = 'activities'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128))
    description = db.Column(db.Text)
    location = db.Column(db.String(128))
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    registration_deadline = db.Column(db.DateTime)
    max_participants = db.Column(db.Integer, default=0)  # 0表示不限制人数
    status = db.Column(db.String(20), default='active')  # active, cancelled, completed
    type = db.Column(db.String(50), default='其他')  # 活动类型：讲座、研讨会、实践活动等
    is_featured = db.Column(db.Boolean, default=False)  # 是否为重点活动
    points = db.Column(db.Integer, default=10)  # 参加活动获得的积分值，默认10分
    created_at = db.Column(db.DateTime, default=lambda: normalize_datetime_for_db(datetime.now()))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    updated_at = db.Column(db.DateTime, default=lambda: normalize_datetime_for_db(datetime.now()), onupdate=lambda: normalize_datetime_for_db(datetime.now()))
    registrations = db.relationship('Registration', backref='activity', lazy='dynamic')
    tags = db.relationship('Tag', secondary=activity_tags, backref=db.backref('activities', lazy='dynamic'))  # 修正多对多关系
    checkin_key = db.Column(db.String(32), nullable=True)  # 签到密钥
    checkin_key_expires = db.Column(db.DateTime, nullable=True)  # 签到密钥过期时间
    checkin_enabled = db.Column(db.Boolean, default=False)  # 手动签到开关
    
    def __repr__(self):
        return f'<Activity {self.title}>'

# 报名模型
class Registration(db.Model):
    __tablename__ = 'registrations'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    activity_id = db.Column(db.Integer, db.ForeignKey('activities.id'))
    register_time = db.Column(db.DateTime, default=lambda: normalize_datetime_for_db(datetime.now()))
    check_in_time = db.Column(db.DateTime, nullable=True)  # 签到时间
    status = db.Column(db.String(20), default='registered')  # registered, cancelled, attended
    remark = db.Column(db.Text)
    
    def __repr__(self):
        return f'<Registration {self.id}>'

# 系统公告表
class Announcement(db.Model):
    __tablename__ = 'announcements'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128))
    content = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=lambda: normalize_datetime_for_db(datetime.now()))
    updated_at = db.Column(db.DateTime, default=lambda: normalize_datetime_for_db(datetime.now()), onupdate=lambda: normalize_datetime_for_db(datetime.now()))
    status = db.Column(db.String(20), default='active')  # active, archived
    
    def __repr__(self):
        return f'<Announcement {self.title}>'

# 系统日志模型
class SystemLog(db.Model):
    __tablename__ = 'system_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(64))
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=lambda: normalize_datetime_for_db(datetime.now()))
    
    def __repr__(self):
        return f'<SystemLog {self.action}>'

# 活动评价模型
class ActivityReview(db.Model):
    __tablename__ = 'activity_reviews'
    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(db.Integer, db.ForeignKey('activities.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5星
    content_quality = db.Column(db.Integer)  # 1-5分
    organization = db.Column(db.Integer)  # 1-5分
    facility = db.Column(db.Integer)  # 1-5分
    review = db.Column(db.Text, nullable=False)
    is_anonymous = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: normalize_datetime_for_db(datetime.now()))
    
    # 关联
    activity = db.relationship('Activity', backref=db.backref('reviews', lazy='dynamic'))
    user = db.relationship('User', backref=db.backref('reviews', lazy='dynamic'))

    @property
    def reviewer_name(self):
        """获取评价者显示名称"""
        if self.is_anonymous:
            return "匿名用户"
        student_info = StudentInfo.query.filter_by(user_id=self.user_id).first()
        return student_info.real_name if student_info else self.user.username

# 标签模型
class Tag(db.Model):
    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, index=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: normalize_datetime_for_db(datetime.now()))
    color = db.Column(db.String(20), default='primary')  # 默认使用 Bootstrap 的 primary 颜色
    # 不再定义 activities 字段，backref 已自动建立

    def __repr__(self):
        return f'<Tag {self.name}>'

# 签到表
class ActivityCheckin(db.Model):
    __tablename__ = 'activity_checkins'
    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(db.Integer, db.ForeignKey('activities.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    checkin_time = db.Column(db.DateTime, default=lambda: normalize_datetime_for_db(datetime.now()))
    status = db.Column(db.String(20), default='checked_in')  # checked_in, late, absent

# 智能推荐系统相关数据结构（预留）
class StudentInterestTag(db.Model):
    __tablename__ = 'student_interest_tags'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student_info.id'), nullable=False)
    tag_id = db.Column(db.Integer, db.ForeignKey('tags.id'), nullable=False)

# AI聊天历史记录模型
class AIChatHistory(db.Model):
    __tablename__ = 'ai_chat_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_id = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # 'user' 或 'assistant'
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: normalize_datetime_for_db(datetime.now()))
    
    def __str__(self):
        return f"{self.role}: {self.content[:20]}..."

# AI聊天会话模型
class AIChatSession(db.Model):
    __tablename__ = 'ai_chat_session'
    id = db.Column(db.String(255), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: normalize_datetime_for_db(datetime.now()))
    updated_at = db.Column(db.DateTime, default=lambda: normalize_datetime_for_db(datetime.now()), onupdate=lambda: normalize_datetime_for_db(datetime.now()))
    
    # 历史记录关联
    messages = db.relationship('AIChatHistory', backref='session', lazy='dynamic',
                              primaryjoin="AIChatHistory.session_id == AIChatSession.id",
                              foreign_keys=[AIChatHistory.session_id],
                              cascade="all, delete-orphan")
    
    def __str__(self):
        return f"Session {self.id} - User {self.user_id}"

# AI用户偏好设置模型
class AIUserPreferences(db.Model):
    __tablename__ = 'ai_user_preferences'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    enable_history = db.Column(db.Boolean, default=True)  # 默认启用历史记录
    max_history_count = db.Column(db.Integer, default=50)  # 每个用户最多保存50条历史记录
    
    def __str__(self):
        return f"AI Preferences for User {self.user_id}"

# 站内信模型
class Message(db.Model):
    __tablename__ = 'message'
    
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: normalize_datetime_for_db(datetime.now()))
    
    # 关系
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_messages')

# 通知模型
class Notification(db.Model):
    __tablename__ = 'notification'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_important = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: normalize_datetime_for_db(datetime.now()))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    expiry_date = db.Column(db.DateTime, nullable=True)
    
    # 关系
    creator = db.relationship('User', backref='created_notifications')
    
# 已读通知关联表
class NotificationRead(db.Model):
    __tablename__ = 'notification_read'
    
    id = db.Column(db.Integer, primary_key=True)
    notification_id = db.Column(db.Integer, db.ForeignKey('notification.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    read_at = db.Column(db.DateTime, default=lambda: normalize_datetime_for_db(datetime.now()))
    
    # 关系
    notification = db.relationship('Notification', backref='read_records')
    user = db.relationship('User', backref='read_notifications')
    
    # 唯一约束，确保一个用户只能标记一个通知为已读一次
    __table_args__ = (db.UniqueConstraint('notification_id', 'user_id', name='uq_notification_user'),)
