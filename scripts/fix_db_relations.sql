-- 修复表关系的SQL脚本
-- 这个脚本会修复roles_users, student_tags, activity_tags表中的外键引用

-- 修复roles_users表
-- 先删除可能存在的旧表
DROP TABLE IF EXISTS roles_users;

-- 创建新的表
CREATE TABLE roles_users (
    user_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles (id) ON DELETE CASCADE
);

-- 修复student_tags表
-- 先删除可能存在的旧表
DROP TABLE IF EXISTS student_tags;

-- 创建新的表
CREATE TABLE student_tags (
    student_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (student_id, tag_id),
    FOREIGN KEY (student_id) REFERENCES student_info (id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
);

-- 修复activity_tags表
-- 先删除可能存在的旧表
DROP TABLE IF EXISTS activity_tags;

-- 创建新的表
CREATE TABLE activity_tags (
    activity_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (activity_id, tag_id),
    FOREIGN KEY (activity_id) REFERENCES activities (id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
);

-- 添加完成消息
DO $$
BEGIN
    RAISE NOTICE '数据库表关系修复完成';
END $$; 