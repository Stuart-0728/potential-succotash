-- 为PostgreSQL数据库添加签到相关字段

-- 检查activities表中是否存在checkin_key列，如果不存在则添加
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name='activities' AND column_name='checkin_key'
    ) THEN
        ALTER TABLE activities ADD COLUMN checkin_key VARCHAR(32);
    END IF;
END $$;

-- 检查activities表中是否存在checkin_key_expires列，如果不存在则添加
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name='activities' AND column_name='checkin_key_expires'
    ) THEN
        ALTER TABLE activities ADD COLUMN checkin_key_expires TIMESTAMP;
    END IF;
END $$;

-- 确保新字段可以为空
ALTER TABLE activities ALTER COLUMN checkin_key DROP NOT NULL;
ALTER TABLE activities ALTER COLUMN checkin_key_expires DROP NOT NULL; 