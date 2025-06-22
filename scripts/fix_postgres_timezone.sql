-- 设置数据库时区为UTC
SET timezone = 'UTC';

-- 检查当前数据库时区
SHOW timezone;

-- 修复活动表中的时间字段
-- 注意：这些操作会将时间转换为UTC时区
-- 如果数据已经是UTC时区，则不会有变化

-- 1. 修复活动开始时间
UPDATE activities
SET start_time = start_time AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
WHERE start_time IS NOT NULL;

-- 2. 修复活动结束时间
UPDATE activities
SET end_time = end_time AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
WHERE end_time IS NOT NULL;

-- 3. 修复活动报名截止时间
UPDATE activities
SET registration_deadline = registration_deadline AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
WHERE registration_deadline IS NOT NULL;

-- 4. 修复活动创建时间
UPDATE activities
SET created_at = created_at AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
WHERE created_at IS NOT NULL;

-- 5. 修复活动更新时间
UPDATE activities
SET updated_at = updated_at AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
WHERE updated_at IS NOT NULL;

-- 修复通知表中的时间字段
-- 1. 修复通知创建时间
UPDATE notification
SET created_at = created_at AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
WHERE created_at IS NOT NULL;

-- 2. 修复通知过期时间
UPDATE notification
SET expiry_date = expiry_date AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
WHERE expiry_date IS NOT NULL;

-- 修复通知已读表中的时间字段
UPDATE notification_read
SET read_at = read_at AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
WHERE read_at IS NOT NULL;

-- 修复站内信表中的时间字段
UPDATE message
SET created_at = created_at AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
WHERE created_at IS NOT NULL;

-- 修复报名表中的时间字段
-- 1. 修复报名时间
UPDATE registrations
SET register_time = register_time AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
WHERE register_time IS NOT NULL;

-- 2. 修复签到时间
UPDATE registrations
SET check_in_time = check_in_time AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
WHERE check_in_time IS NOT NULL;

-- 修复系统日志表中的时间字段
UPDATE system_logs
SET created_at = created_at AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
WHERE created_at IS NOT NULL;

-- 修复积分历史表中的时间字段
UPDATE points_history
SET created_at = created_at AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
WHERE created_at IS NOT NULL;

-- 修复活动评价表中的时间字段
UPDATE activity_reviews
SET created_at = created_at AT TIME ZONE 'Asia/Shanghai' AT TIME ZONE 'UTC'
WHERE created_at IS NOT NULL; 