-- 更新Render PostgreSQL数据库
-- 执行日期: 2025-06-19

-- 创建AI聊天历史记录表（如果不存在）
CREATE TABLE IF NOT EXISTS ai_chat_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    session_id VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 创建AI聊天会话表（如果不存在）
CREATE TABLE IF NOT EXISTS ai_chat_session (
    id VARCHAR(255) PRIMARY KEY,
    user_id INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 创建用户AI偏好设置表（如果不存在）
CREATE TABLE IF NOT EXISTS ai_user_preferences (
    user_id INTEGER PRIMARY KEY,
    enable_history BOOLEAN DEFAULT TRUE,
    max_history_count INTEGER DEFAULT 50,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 创建索引以提高查询性能
-- 检查索引是否已存在
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relname = 'idx_ai_chat_history_user_id'
        AND n.nspname = current_schema()
    ) THEN
        -- 创建用户ID索引
        CREATE INDEX idx_ai_chat_history_user_id ON ai_chat_history(user_id);
        RAISE NOTICE '创建了用户ID索引';
    ELSE
        RAISE NOTICE '用户ID索引已存在，无需创建';
    END IF;
END $$;

-- 检查会话ID索引是否已存在
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relname = 'idx_ai_chat_history_session_id'
        AND n.nspname = current_schema()
    ) THEN
        -- 创建会话ID索引
        CREATE INDEX idx_ai_chat_history_session_id ON ai_chat_history(session_id);
        RAISE NOTICE '创建了会话ID索引';
    ELSE
        RAISE NOTICE '会话ID索引已存在，无需创建';
    END IF;
END $$;

-- 确保activities表有checkin_enabled字段
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name='activities' AND column_name='checkin_enabled'
    ) THEN
        ALTER TABLE activities ADD COLUMN checkin_enabled BOOLEAN DEFAULT FALSE;
        RAISE NOTICE '添加了checkin_enabled字段';
    ELSE
        RAISE NOTICE 'checkin_enabled字段已存在，无需添加';
    END IF;
END $$;

-- 修复roles_users表
-- 先删除可能存在的旧表
DROP TABLE IF EXISTS roles_users;

-- 创建新的表
CREATE TABLE roles_users (
    user_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles (id) ON DELETE CASCADE
);

-- 修复student_tags表
-- 先删除可能存在的旧表
DROP TABLE IF EXISTS student_tags;

-- 创建新的表
CREATE TABLE student_tags (
    student_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (student_id, tag_id),
    FOREIGN KEY (student_id) REFERENCES student_info (id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
);

-- 修复activity_tags表
-- 先删除可能存在的旧表
DROP TABLE IF EXISTS activity_tags;

-- 创建新的表
CREATE TABLE activity_tags (
    activity_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (activity_id, tag_id),
    FOREIGN KEY (activity_id) REFERENCES activities (id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
);

-- 为所有现有用户创建AI用户偏好设置记录（如果不存在）
INSERT INTO ai_user_preferences (user_id, enable_history, max_history_count)
SELECT id, true, CASE WHEN role_id = 1 THEN 100 ELSE 50 END
FROM users
WHERE id NOT IN (SELECT user_id FROM ai_user_preferences);

-- 完成提示
DO $$
BEGIN
    RAISE NOTICE '数据库更新完成';
END $$;

-- 重置Render数据库后的初始化SQL脚本
-- 用于创建必要的表格和初始管理员账户

-- 创建角色表
CREATE TABLE IF NOT EXISTS roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(64) UNIQUE NOT NULL,
    description VARCHAR(128)
);

-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE,
    password_hash VARCHAR(256) NOT NULL,
    role_id INTEGER REFERENCES roles(id),
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITHOUT TIME ZONE
);

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

-- 重置序列，确保自增ID正确
SELECT setval('roles_id_seq', (SELECT MAX(id) FROM roles));
SELECT setval('users_id_seq', (SELECT MAX(id) FROM users));

-- 输出提示
DO $$
BEGIN
    RAISE NOTICE '数据库初始化完成! 初始管理员账号: admin, 密码: admin123';
END $$;

-- 更新Render PostgreSQL数据库的脚本
-- 用于修复消息和通知系统的表结构和外键引用

-- 检查是否存在旧的消息表，如果存在则删除
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'message') THEN
        DROP TABLE IF EXISTS notification_read;
        DROP TABLE IF EXISTS notification;
        DROP TABLE IF EXISTS message;
    END IF;
END $$;

-- 添加站内信表
CREATE TABLE IF NOT EXISTS message (
    id SERIAL PRIMARY KEY,
    sender_id INTEGER NOT NULL,
    receiver_id INTEGER NOT NULL,
    subject VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sender_id) REFERENCES users(id),
    FOREIGN KEY (receiver_id) REFERENCES users(id)
);

-- 添加通知表
CREATE TABLE IF NOT EXISTS notification (
    id SERIAL PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    is_important BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER NOT NULL,
    expiry_date TIMESTAMP WITH TIME ZONE,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- 添加通知已读表
CREATE TABLE IF NOT EXISTS notification_read (
    id SERIAL PRIMARY KEY,
    notification_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    read_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (notification_id) REFERENCES notification(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE (notification_id, user_id)
);

-- 创建相应的序列
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'message') THEN
        IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'message_id_seq') THEN
            CREATE SEQUENCE message_id_seq;
            ALTER TABLE message ALTER COLUMN id SET DEFAULT nextval('message_id_seq');
            SELECT setval('message_id_seq', COALESCE((SELECT MAX(id) FROM message), 0) + 1);
        END IF;
    END IF;

    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'notification') THEN
        IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'notification_id_seq') THEN
            CREATE SEQUENCE notification_id_seq;
            ALTER TABLE notification ALTER COLUMN id SET DEFAULT nextval('notification_id_seq');
            SELECT setval('notification_id_seq', COALESCE((SELECT MAX(id) FROM notification), 0) + 1);
        END IF;
    END IF;

    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'notification_read') THEN
        IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'notification_read_id_seq') THEN
            CREATE SEQUENCE notification_read_id_seq;
            ALTER TABLE notification_read ALTER COLUMN id SET DEFAULT nextval('notification_read_id_seq');
            SELECT setval('notification_read_id_seq', COALESCE((SELECT MAX(id) FROM notification_read), 0) + 1);
        END IF;
    END IF;
END $$; 