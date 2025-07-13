-- 删除所有现有表
DROP TABLE IF EXISTS points_history;
DROP TABLE IF EXISTS system_logs;
DROP TABLE IF EXISTS announcements;
DROP TABLE IF EXISTS activity_checkins;
DROP TABLE IF EXISTS activity_reviews;
DROP TABLE IF EXISTS student_interest_tags;
DROP TABLE IF EXISTS activity_tags;
DROP TABLE IF EXISTS registrations;
DROP TABLE IF EXISTS activities;
DROP TABLE IF EXISTS tags;
DROP TABLE IF EXISTS student_info;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS roles;

-- 重新创建表结构
-- 角色表
CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(64) UNIQUE NOT NULL,
    description VARCHAR(128)
);

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(64) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    role_id INTEGER REFERENCES roles(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- 学生信息表
CREATE TABLE IF NOT EXISTS student_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE REFERENCES users(id),
    student_id VARCHAR(20) UNIQUE,
    real_name VARCHAR(50),
    gender VARCHAR(10),
    grade VARCHAR(20),
    college VARCHAR(100),
    major VARCHAR(100),
    phone VARCHAR(20),
    qq VARCHAR(20),
    points INTEGER DEFAULT 0,
    has_selected_tags BOOLEAN DEFAULT FALSE
);

-- 标签表
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(64) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    color VARCHAR(20) DEFAULT 'primary'
);

-- 活动表
CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(128) NOT NULL,
    description TEXT,
    location VARCHAR(128),
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    registration_deadline TIMESTAMP,
    max_participants INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active',
    is_featured BOOLEAN DEFAULT FALSE,
    points INTEGER DEFAULT 10,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    checkin_key VARCHAR(32),
    checkin_key_expires TIMESTAMP
);

-- 报名表
CREATE TABLE IF NOT EXISTS registrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    activity_id INTEGER REFERENCES activities(id),
    register_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    check_in_time TIMESTAMP,
    status VARCHAR(20) DEFAULT 'registered',
    remark TEXT
);

-- 活动-标签关联表
CREATE TABLE IF NOT EXISTS activity_tags (
    activity_id INTEGER REFERENCES activities(id),
    tag_id INTEGER REFERENCES tags(id),
    PRIMARY KEY (activity_id, tag_id)
);

-- 学生兴趣标签关联表
CREATE TABLE IF NOT EXISTS student_interest_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER REFERENCES student_info(id) NOT NULL,
    tag_id INTEGER REFERENCES tags(id) NOT NULL
);

-- 活动评价表
CREATE TABLE IF NOT EXISTS activity_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id INTEGER REFERENCES activities(id) NOT NULL,
    user_id INTEGER REFERENCES users(id) NOT NULL,
    rating INTEGER NOT NULL,
    content_quality INTEGER,
    organization INTEGER,
    facility INTEGER,
    review TEXT NOT NULL,
    is_anonymous BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 活动签到表
CREATE TABLE IF NOT EXISTS activity_checkins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id INTEGER REFERENCES activities(id),
    user_id INTEGER REFERENCES users(id),
    checkin_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'checked_in'
);

-- 系统公告表
CREATE TABLE IF NOT EXISTS announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(128),
    content TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active'
);

-- 系统日志表
CREATE TABLE IF NOT EXISTS system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(64),
    details TEXT,
    ip_address VARCHAR(64),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 积分历史表
CREATE TABLE IF NOT EXISTS points_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER REFERENCES student_info(id),
    points INTEGER,
    reason VARCHAR(200),
    activity_id INTEGER REFERENCES activities(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 插入默认角色
INSERT INTO roles (name, description) VALUES 
('Admin', '管理员'),
('Student', '学生');

-- 插入默认管理员账号
INSERT INTO users (username, email, password_hash, role_id) VALUES 
('admin', 'admin@example.com', 'pbkdf2:sha256:150000$OhKkdPsK$d9a0e8a3a9b7c1c8f2b0e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e7d6c5b4a3', 1); 