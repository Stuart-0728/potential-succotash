-- Render PostgreSQL 数据库重置脚本
-- 用于重置数据库并创建必要的初始结构

-- 删除所有表格（按顺序删除以避免外键约束问题）
DO $$ 
DECLARE
    r RECORD;
BEGIN
    -- 禁用触发器
    EXECUTE 'SET session_replication_role = replica';
    
    -- 删除所有表格
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
        EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
    END LOOP;
    
    -- 恢复触发器
    EXECUTE 'SET session_replication_role = DEFAULT';
    
    RAISE NOTICE '所有表格已删除';
END $$;

-- 创建基本表结构 --

-- 创建角色表
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(64) UNIQUE NOT NULL,
    description VARCHAR(128)
);

-- 创建用户表
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE,
    password_hash VARCHAR(256) NOT NULL,
    role_id INTEGER REFERENCES roles(id),
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITHOUT TIME ZONE
);

-- 创建学生信息表
CREATE TABLE student_info (
    id SERIAL PRIMARY KEY,
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
    has_selected_tags BOOLEAN DEFAULT false
);

-- 创建标签表
CREATE TABLE tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(64) UNIQUE,
    description TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    color VARCHAR(20) DEFAULT 'primary'
);

-- 创建学生与标签关系表
CREATE TABLE student_tags (
    student_id INTEGER REFERENCES student_info(id),
    tag_id INTEGER REFERENCES tags(id),
    PRIMARY KEY (student_id, tag_id)
);

-- 创建活动表
CREATE TABLE activities (
    id SERIAL PRIMARY KEY,
    title VARCHAR(128) NOT NULL,
    description TEXT,
    location VARCHAR(128),
    start_time TIMESTAMP WITHOUT TIME ZONE,
    end_time TIMESTAMP WITHOUT TIME ZONE,
    registration_deadline TIMESTAMP WITHOUT TIME ZONE,
    max_participants INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active',
    type VARCHAR(50) DEFAULT '其他',
    is_featured BOOLEAN DEFAULT false,
    points INTEGER DEFAULT 10,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    checkin_key VARCHAR(32),
    checkin_key_expires TIMESTAMP WITHOUT TIME ZONE,
    checkin_enabled BOOLEAN DEFAULT false
);

-- 创建活动与标签关系表
CREATE TABLE activity_tags (
    activity_id INTEGER REFERENCES activities(id),
    tag_id INTEGER REFERENCES tags(id),
    PRIMARY KEY (activity_id, tag_id)
);

-- 创建报名表
CREATE TABLE registrations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    activity_id INTEGER REFERENCES activities(id),
    register_time TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    check_in_time TIMESTAMP WITHOUT TIME ZONE,
    status VARCHAR(20) DEFAULT 'registered',
    remark TEXT
);

-- 创建积分历史表
CREATE TABLE points_history (
    id SERIAL PRIMARY KEY,
    student_id INTEGER REFERENCES student_info(id),
    points INTEGER,
    reason VARCHAR(200),
    activity_id INTEGER REFERENCES activities(id),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建活动评价表
CREATE TABLE activity_reviews (
    id SERIAL PRIMARY KEY,
    activity_id INTEGER NOT NULL REFERENCES activities(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    rating INTEGER NOT NULL,
    content_quality INTEGER,
    organization INTEGER,
    facility INTEGER,
    review TEXT NOT NULL,
    is_anonymous BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建活动签到表
CREATE TABLE activity_checkins (
    id SERIAL PRIMARY KEY,
    activity_id INTEGER REFERENCES activities(id),
    user_id INTEGER REFERENCES users(id),
    checkin_time TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'checked_in'
);

-- 创建系统日志表
CREATE TABLE system_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(64),
    details TEXT,
    ip_address VARCHAR(64),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建AI聊天相关表格
CREATE TABLE ai_chat_session (
    id VARCHAR(255) PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ai_chat_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    session_id VARCHAR(255) NOT NULL REFERENCES ai_chat_session(id),
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ai_user_preferences (
    user_id INTEGER PRIMARY KEY REFERENCES users(id),
    enable_history BOOLEAN DEFAULT true,
    max_history_count INTEGER DEFAULT 50
);

-- 插入初始数据 --

-- 插入角色数据
INSERT INTO roles (id, name, description) VALUES
    (1, 'Admin', '管理员'),
    (2, 'Student', '学生')
ON CONFLICT (id) DO NOTHING;

-- 插入管理员用户 (密码为 admin123)
INSERT INTO users (username, email, password_hash, role_id, active)
VALUES (
    'admin',
    'admin@example.com',
    'pbkdf2:sha256:260000$ZL9jQCnF$14a020852b4030ecc646fbbf5cd5466c622a9edacbc36bdfcb7b2587d2438b3a',
    1,
    true
)
ON CONFLICT (username) DO NOTHING;

-- 插入测试标签
INSERT INTO tags (name, description, color) VALUES
    ('学术讲座', '学术类讲座和研讨会', 'primary'),
    ('志愿服务', '志愿者活动和社区服务', 'success'),
    ('体育活动', '各类体育比赛和运动活动', 'danger'),
    ('文艺活动', '文学艺术相关活动', 'warning'),
    ('就业指导', '就业相关培训和指导', 'info')
ON CONFLICT (name) DO NOTHING;

-- 重置序列，确保自增ID正确
SELECT setval('roles_id_seq', (SELECT MAX(id) FROM roles));
SELECT setval('users_id_seq', (SELECT MAX(id) FROM users));
SELECT setval('tags_id_seq', (SELECT MAX(id) FROM tags));

-- 输出提示
DO $$
BEGIN
    RAISE NOTICE '数据库初始化完成! 初始管理员账号: admin, 密码: admin123';
END $$; 