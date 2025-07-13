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
    checkin_key = db.Column(db.String(32), nullable=True)  # 签到密钥
    checkin_key_expires = db.Column(db.DateTime, nullable=True)  # 签到密钥过期时间
    
    def __repr__(self):
        return f'<Activity {self.title}>' 