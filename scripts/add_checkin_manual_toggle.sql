-- 为PostgreSQL数据库添加手动签到开关字段

-- 检查activities表中是否存在checkin_enabled列，如果不存在则添加
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name='activities' AND column_name='checkin_enabled'
    ) THEN
        ALTER TABLE activities ADD COLUMN checkin_enabled BOOLEAN DEFAULT FALSE;
    END IF;
END $$; 