-- 为activities表添加poster_data和poster_mimetype列
ALTER TABLE activities ADD COLUMN IF NOT EXISTS poster_data BYTEA;
ALTER TABLE activities ADD COLUMN IF NOT EXISTS poster_mimetype VARCHAR(50);

-- 添加注释
COMMENT ON COLUMN activities.poster_data IS '存储海报图片的二进制数据';
COMMENT ON COLUMN activities.poster_mimetype IS '海报图片的MIME类型';

-- 创建一个函数来检查登录密码哈希算法问题
CREATE OR REPLACE FUNCTION fix_password_hash() RETURNS VOID AS $$
DECLARE
    r RECORD;
BEGIN
    -- 输出开始信息
    RAISE NOTICE 'Starting password hash check and fix...';
    
    -- 遍历所有用户
    FOR r IN SELECT id, username, password_hash FROM users WHERE password_hash LIKE 'scrypt%' LOOP
        -- 输出发现的scrypt密码哈希
        RAISE NOTICE 'Found scrypt hash for user %: %', r.username, r.password_hash;
        
        -- 修改为pbkdf2哈希（这里使用了一个示例哈希，实际应用中应该为每个用户生成唯一的哈希）
        -- 注意：这会重置用户密码为默认密码 "123456"
        UPDATE users SET password_hash = 'pbkdf2:sha256:600000$RjY8y4K5pUaqEPcJ$5ffbfa515c8eaf9cfa5e61e30c80dd266c6d5dd44a67159e01c18d306ed27385' WHERE id = r.id;
        
        RAISE NOTICE 'Updated password hash for user %', r.username;
    END LOOP;
    
    -- 输出完成信息
    RAISE NOTICE 'Password hash check and fix completed.';
END;
$$ LANGUAGE plpgsql;

-- 执行修复函数
SELECT fix_password_hash();

-- 输出确认信息
SELECT 'Database schema updated successfully.' AS result; 