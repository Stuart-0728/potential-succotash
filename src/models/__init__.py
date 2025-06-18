from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# 用户角色表
class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    description = db.Column(db.String(128))  # 新增，支持角色描述
    users = db.relationship('User', backref=db.backref('role', lazy='joined'), lazy='dynamic')

    def __repr__(self):
        return f'<Role {self.name}>'

# 用户表
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    email = db.Column(db.String(120), unique=True, index=True)
    password_hash = db.Column(db.String(256))  # 已修改：从128扩展到256
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    student_info = db.relationship('StudentInfo', backref='user', uselist=False)
    registrations = db.relationship('Registration', backref='user', lazy='dynamic')
    created_at = db.Column(db.DateTime, default=datetime.now)
    last_login = db.Column(db.DateTime)

    def __repr__(self):
        return f'<User {self.username}>'

# 学生信息表
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
    tags = db.relationship('Tag', secondary='student_interest_tags', backref=db.backref('students', lazy='dynamic'))  # 多对多

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# 活动表
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
    is_featured = db.Column(db.Boolean, default=False)  # 是否为重点活动
    points = db.Column(db.Integer, default=10)  # 参加活动获得的积分值，默认10分
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    registrations = db.relationship('Registration', backref='activity', lazy='dynamic')
    tags = db.relationship('Tag', secondary='activity_tags', backref=db.backref('activities', lazy='dynamic'))  # 修正多对多关系
    
    def __repr__(self):
        return f'<Activity {self.title}>'

# 活动报名表
class Registration(db.Model):
    __tablename__ = 'registrations'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    activity_id = db.Column(db.Integer, db.ForeignKey('activities.id'))
    register_time = db.Column(db.DateTime, default=datetime.now)
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
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    status = db.Column(db.String(20), default='active')  # active, archived
    
    def __repr__(self):
        return f'<Announcement {self.title}>'

# 系统日志表
class SystemLog(db.Model):
    __tablename__ = 'system_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(64))
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def __repr__(self):
        return f'<SystemLog {self.action}>'

# 活动评价表
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
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

# 标签表
class Tag(db.Model):
    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, index=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    color = db.Column(db.String(20), default='primary')  # 默认使用 Bootstrap 的 primary 颜色
    # 不再定义 activities 字段，backref 已自动建立

    def __repr__(self):
        return f'<Tag {self.name}>'

# 活动-标签多对多辅助表
activity_tags = db.Table(
    'activity_tags',
    db.Column('activity_id', db.Integer, db.ForeignKey('activities.id')),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'))
)

# 签到表
class ActivityCheckin(db.Model):
    __tablename__ = 'activity_checkins'
    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(db.Integer, db.ForeignKey('activities.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    checkin_time = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='checked_in')  # checked_in, late, absent

# 智能推荐系统相关数据结构（预留）
class StudentInterestTag(db.Model):
    __tablename__ = 'student_interest_tags'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student_info.id'), nullable=False)
    tag_id = db.Column(db.Integer, db.ForeignKey('tags.id'), nullable=False)
