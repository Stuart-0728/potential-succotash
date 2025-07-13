-- PostgreSQL版本的AI聊天相关表
-- 为Render远程数据库创建

-- AI聊天历史记录表
CREATE TABLE IF NOT EXISTS ai_chat_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    session_id VARCHAR(255) NOT NULL,  -- 会话ID
    role VARCHAR(50) NOT NULL,  -- 'user' 或 'assistant'
    content TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- AI聊天会话表
CREATE TABLE IF NOT EXISTS ai_chat_session (
    id VARCHAR(255) PRIMARY KEY,
    user_id INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 用户AI偏好设置表
CREATE TABLE IF NOT EXISTS ai_user_preferences (
    user_id INTEGER PRIMARY KEY, -- 直接使用user_id作为主键
    enable_history BOOLEAN DEFAULT TRUE, -- 默认存储历史记录
    max_history_count INTEGER DEFAULT 50, -- 每个用户最多保存50条历史记录
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_ai_chat_user_id ON ai_chat_history(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_chat_session_id ON ai_chat_history(session_id); 