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