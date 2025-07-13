-- 为 users 表添加邮箱验证相关字段

-- 检查 email_confirmed 字段是否存在，如果不存在则添加
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_confirmed BOOLEAN DEFAULT FALSE;

-- 检查 confirmation_token 字段是否存在，如果不存在则添加
ALTER TABLE users ADD COLUMN IF NOT EXISTS confirmation_token VARCHAR(128);

-- 检查 confirmation_token_expires 字段是否存在，如果不存在则添加
ALTER TABLE users ADD COLUMN IF NOT EXISTS confirmation_token_expires TIMESTAMP WITH TIME ZONE;

-- 为管理员用户自动设置邮箱已验证
UPDATE users
SET email_confirmed = TRUE
WHERE id IN (
    SELECT u.id 
    FROM users u
    JOIN roles r ON u.role_id = r.id
    WHERE r.name = 'Admin'
);

-- 添加索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_users_email_confirmed ON users (email_confirmed);
CREATE INDEX IF NOT EXISTS idx_users_confirmation_token ON users (confirmation_token);

-- SQLite版本
-- ALTER TABLE users ADD COLUMN email_confirmed BOOLEAN DEFAULT FALSE;
-- ALTER TABLE users ADD COLUMN confirmation_token VARCHAR(128);
-- ALTER TABLE users ADD COLUMN confirmation_token_expires TIMESTAMP;
-- 
-- UPDATE users
-- SET email_confirmed = 1
-- WHERE id IN (
--     SELECT u.id 
--     FROM users u
--     JOIN roles r ON u.role_id = r.id
--     WHERE r.name = 'Admin'
-- );
-- 
-- CREATE INDEX idx_users_email_confirmed ON users (email_confirmed);
-- CREATE INDEX idx_users_confirmation_token ON users (confirmation_token); 