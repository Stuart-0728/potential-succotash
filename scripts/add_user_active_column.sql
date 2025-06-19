-- 为users表添加active列
-- 这个脚本检查users表是否存在active列，如果不存在则添加

DO $$
BEGIN
    -- 检查列是否已存在
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'users' AND column_name = 'active'
    ) THEN
        -- 添加active列，默认值为true
        ALTER TABLE users ADD COLUMN active BOOLEAN DEFAULT TRUE;
        RAISE NOTICE 'users表添加了active列';
    ELSE
        RAISE NOTICE 'users表已有active列，无需添加';
    END IF;
END $$; 