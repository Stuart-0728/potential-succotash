-- 更新 activities 表中的 checkin_key_expires 列为 timestamptz 类型
ALTER TABLE activities 
ALTER COLUMN checkin_key_expires TYPE timestamptz 
USING checkin_key_expires AT TIME ZONE 'UTC';

-- 确保所有时间字段都使用 timestamptz
COMMENT ON COLUMN activities.checkin_key_expires IS '签到密钥过期时间 (带时区)';
