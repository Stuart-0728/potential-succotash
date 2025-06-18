-- 为SQLite数据库添加手动签到开关字段

-- SQLite不支持IF NOT EXISTS语法，所以我们使用PRAGMA table_info来检查列是否存在
-- 这个脚本将在应用程序中执行，而不是直接在SQLite命令行中执行

-- 添加checkin_enabled列
ALTER TABLE activities ADD COLUMN checkin_enabled BOOLEAN DEFAULT FALSE; 