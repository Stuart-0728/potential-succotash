-- 检查activities表中的列
.headers on
.mode column
PRAGMA table_info(activities);

-- 尝试添加列（如果不存在）
-- 注意：这些语句可能会失败，如果列已存在，但SQLite会继续执行后续语句
BEGIN TRANSACTION;

-- 尝试添加checkin_key列
ALTER TABLE activities ADD COLUMN checkin_key VARCHAR(32);

-- 尝试添加checkin_key_expires列
ALTER TABLE activities ADD COLUMN checkin_key_expires TIMESTAMP;

COMMIT; 