-- 为PostgreSQL添加AI聊天历史记录的用户索引
-- 这将提高根据用户ID查询和删除聊天记录的性能

-- 检查索引是否已存在
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relname = 'idx_ai_chat_history_user_id'
        AND n.nspname = current_schema()
    ) THEN
        -- 创建索引
        CREATE INDEX idx_ai_chat_history_user_id ON ai_chat_history(user_id);
        RAISE NOTICE '创建了用户ID索引';
    ELSE
        RAISE NOTICE '用户ID索引已存在，无需创建';
    END IF;
END $$; 