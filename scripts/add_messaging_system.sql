-- 添加站内信表
CREATE TABLE IF NOT EXISTS message (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER NOT NULL,
    receiver_id INTEGER NOT NULL,
    subject VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    is_read BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sender_id) REFERENCES users(id),
    FOREIGN KEY (receiver_id) REFERENCES users(id)
);

-- 添加通知表
CREATE TABLE IF NOT EXISTS notification (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    is_important BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER NOT NULL,
    expiry_date DATETIME,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- 添加通知已读表
CREATE TABLE IF NOT EXISTS notification_read (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notification_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    read_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (notification_id) REFERENCES notification(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE (notification_id, user_id)
);

-- 为PostgreSQL创建相应的序列
-- 这部分只在PostgreSQL环境中执行，SQLite会忽略
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'message') THEN
        IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'message_id_seq') THEN
            CREATE SEQUENCE message_id_seq;
            ALTER TABLE message ALTER COLUMN id SET DEFAULT nextval('message_id_seq');
            SELECT setval('message_id_seq', COALESCE((SELECT MAX(id) FROM message), 0) + 1);
        END IF;
    END IF;

    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'notification') THEN
        IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'notification_id_seq') THEN
            CREATE SEQUENCE notification_id_seq;
            ALTER TABLE notification ALTER COLUMN id SET DEFAULT nextval('notification_id_seq');
            SELECT setval('notification_id_seq', COALESCE((SELECT MAX(id) FROM notification), 0) + 1);
        END IF;
    END IF;

    IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'notification_read') THEN
        IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'notification_read_id_seq') THEN
            CREATE SEQUENCE notification_read_id_seq;
            ALTER TABLE notification_read ALTER COLUMN id SET DEFAULT nextval('notification_read_id_seq');
            SELECT setval('notification_read_id_seq', COALESCE((SELECT MAX(id) FROM notification_read), 0) + 1);
        END IF;
    END IF;
END $$; 