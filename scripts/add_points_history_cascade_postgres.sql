-- 为PostgreSQL数据库的points_history表添加级联删除外键约束
-- 这个脚本用于解决删除活动时遇到的外键约束错误

-- 首先删除现有的外键约束
ALTER TABLE points_history DROP CONSTRAINT IF EXISTS points_history_activity_id_fkey;

-- 然后添加新的带有CASCADE选项的外键约束
ALTER TABLE points_history 
    ADD CONSTRAINT points_history_activity_id_fkey 
    FOREIGN KEY (activity_id) 
    REFERENCES activities(id) 
    ON DELETE CASCADE;

-- 完成消息
DO $$
BEGIN
    RAISE NOTICE 'points_history表外键约束修复完成';
END $$; 