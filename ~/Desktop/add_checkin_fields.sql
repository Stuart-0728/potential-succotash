-- 添加签到密钥和过期时间字段到activities表
ALTER TABLE activities ADD COLUMN IF NOT EXISTS checkin_key VARCHAR(32);
ALTER TABLE activities ADD COLUMN IF NOT EXISTS checkin_key_expires TIMESTAMP;

-- 确保新字段可以为空
ALTER TABLE activities ALTER COLUMN checkin_key DROP NOT NULL;
ALTER TABLE activities ALTER COLUMN checkin_key_expires DROP NOT NULL;

-- 验证字段添加成功
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'activities' AND (column_name = 'checkin_key' OR column_name = 'checkin_key_expires'); 