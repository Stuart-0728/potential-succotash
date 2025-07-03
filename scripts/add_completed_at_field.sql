-- 添加completed_at字段到activities表
ALTER TABLE activities ADD COLUMN completed_at TIMESTAMP WITH TIME ZONE;
 
-- 更新已完成活动的completed_at字段为当前时间
UPDATE activities 
SET completed_at = NOW() 
WHERE status = 'completed' AND completed_at IS NULL; 