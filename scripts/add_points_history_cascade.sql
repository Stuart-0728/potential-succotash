-- 为points_history表添加级联删除外键约束
-- 这个脚本用于解决删除活动时遇到的外键约束错误

-- PostgreSQL版本
-- 首先删除现有的外键约束
ALTER TABLE points_history DROP CONSTRAINT IF EXISTS points_history_activity_id_fkey;

-- 然后添加新的带有CASCADE选项的外键约束
ALTER TABLE points_history 
    ADD CONSTRAINT points_history_activity_id_fkey 
    FOREIGN KEY (activity_id) 
    REFERENCES activities(id) 
    ON DELETE CASCADE;

-- SQLite版本
-- 注意：SQLite不支持ALTER TABLE DROP CONSTRAINT语法
-- 对于SQLite，需要使用以下步骤：
-- 1. 创建新表（带有正确的约束）
-- 2. 复制数据
-- 3. 删除旧表
-- 4. 重命名新表

-- 这些操作应该在应用程序代码中执行，而不是直接在SQLite中执行
-- 以下是应用程序中可以使用的SQL语句

-- 创建临时表
CREATE TABLE IF NOT EXISTS points_history_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER REFERENCES student_info(id),
    points INTEGER,
    reason VARCHAR(200),
    activity_id INTEGER REFERENCES activities(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 复制数据
INSERT INTO points_history_new 
SELECT id, student_id, points, reason, activity_id, created_at 
FROM points_history;

-- 删除旧表
DROP TABLE points_history;

-- 重命名新表
ALTER TABLE points_history_new RENAME TO points_history;

-- 完成消息
SELECT 'points_history表外键约束修复完成' AS message; 