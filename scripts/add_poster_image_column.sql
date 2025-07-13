-- 为activities表添加poster_image列
ALTER TABLE activities ADD COLUMN IF NOT EXISTS poster_image VARCHAR(255);

-- 添加日志信息
INSERT INTO system_logs (action, details, created_at)
VALUES ('database_update', 'Added poster_image column to activities table', NOW());

-- 显示确认信息
SELECT 'Successfully added poster_image column to activities table' AS result; 