# 数据库更新说明

本次更新包含AI聊天历史记录相关功能的增强，主要改进有：

1. 添加了清除所有聊天历史记录的功能
2. 优化了数据库索引以提高查询和删除操作性能
3. 增加了用户级别的聊天历史管理

## 最新更新（2025-06-20）

本次更新修复了以下问题：

1. **时区问题修复**：确保所有时间相关功能使用北京时间
2. **活动删除问题修复**：修复了删除活动时的外键约束错误

### 时区修复

- 修改了`get_beijing_time()`函数，确保始终返回正确的北京时间
- 更新了`get_localized_now()`函数，使其调用`get_beijing_time()`保持一致性
- 改进了`LocalizedDateTimeField`类，确保表单数据正确添加时区信息
- 确保全局上下文中注入的`now`变量使用正确的北京时间
- 优化了签到模态框模板，添加了服务器时间显示

### 积分历史记录外键约束修复

- 修改了`points_history`表的外键约束，添加了`ON DELETE CASCADE`选项
- 创建了两个SQL脚本：`add_points_history_cascade_sqlite.sql`和`add_points_history_cascade_postgres.sql`
- 现在可以安全地删除活动，相关的积分历史记录会自动删除
- 此修复解决了删除活动时出现的外键约束错误

## 数据库更新步骤

### 本地开发环境 (SQLite)

本地SQLite数据库不需要额外操作，应用程序启动时会自动创建必要的表和索引。

对于积分历史记录外键约束修复，请执行：

```bash
sqlite3 instance/cqnu_association.db < scripts/add_points_history_cascade_sqlite.sql
```

### 生产环境 (PostgreSQL on Render)

按照以下步骤更新Render上的PostgreSQL数据库：

1. 连接到Render PostgreSQL数据库：

```bash
PGPASSWORD=BamPWSRTgj0sPGKM4sGsLDv8sGCPCPzB psql -h dpg-d0sjag49c44c73f7jt4g-a.oregon-postgres.render.com -U cqnu_association_uxft_user cqnu_association_uxft
```

2. 确保AI聊天相关表已创建（如果未创建，请执行以下命令）：

```sql
\i scripts/update_render_postgres.sql
```

3. 添加性能优化索引：

```sql
\i scripts/add_ai_chat_user_index.sql
```

4. 修复积分历史记录外键约束：

```sql
\i scripts/add_points_history_cascade_postgres.sql
```

5. 验证外键约束已正确修改：

```sql
SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid = 'points_history'::regclass;
```

## 功能说明

### 聊天历史管理

本次更新增加了两种清除聊天历史的方式：

1. **清除当前对话**：仅清除当前会话的聊天记录
2. **清除所有历史**：清除该用户的所有聊天记录

这两个功能可在聊天窗口底部的操作栏中找到。

### 数据库占用考虑

AI聊天记录可能会随着时间增长而占用较多数据库空间。系统已经采取了以下措施来控制数据库大小：

1. 每个用户的历史记录默认限制为最近50条（可通过`AIUserPreferences`表中的`max_history_count`字段调整）
2. 用户可以随时手动清除历史记录
3. 添加了索引以提高查询和删除操作的性能

### 未来可能的优化

1. 添加自动清除过期聊天记录的定时任务
2. 在管理员界面添加聊天记录使用情况的统计和管理功能
3. 实现按时间范围批量清除聊天记录的功能

# 数据库更新指南

本文档提供了在Render平台上更新数据库结构的详细步骤。

## 最新更新内容

1. 修复了消息和通知系统的表结构和外键引用
2. 优化了时区处理逻辑，确保在Render环境中正确处理UTC时间

## 在Render平台上执行数据库迁移

### 方法1：使用Render PostgreSQL控制台

1. 登录Render控制台
2. 导航到PostgreSQL数据库服务
3. 点击"Shell"按钮打开数据库控制台
4. 复制`update_render_db.sql`文件中的内容
5. 在控制台中粘贴并执行SQL脚本
6. 验证表结构是否创建成功：
   ```sql
   \dt
   \d message
   \d notification
   \d notification_read
   ```

### 方法2：使用reset_render_db_auto.py脚本

1. 确保已设置以下环境变量：
   - `RENDER_POSTGRES_HOST`：数据库主机地址
   - `RENDER_POSTGRES_PORT`：数据库端口
   - `RENDER_POSTGRES_USER`：数据库用户名
   - `RENDER_POSTGRES_PASSWORD`：数据库密码
   - `RENDER_POSTGRES_DB`：数据库名称

2. 执行自动更新脚本：
   ```bash
   python reset_render_db_auto.py
   ```

## 验证数据库更新

执行以下SQL查询确认表结构是否正确：

```sql
-- 检查消息表
SELECT table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'message'
ORDER BY ordinal_position;

-- 检查通知表
SELECT table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'notification'
ORDER BY ordinal_position;

-- 检查通知已读表
SELECT table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'notification_read'
ORDER BY ordinal_position;

-- 检查外键约束
SELECT
    tc.table_schema, 
    tc.constraint_name, 
    tc.table_name, 
    kcu.column_name, 
    ccu.table_schema AS foreign_table_schema,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name 
FROM 
    information_schema.table_constraints AS tc 
    JOIN information_schema.key_column_usage AS kcu
      ON tc.constraint_name = kcu.constraint_name
      AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage AS ccu
      ON ccu.constraint_name = tc.constraint_name
      AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name IN ('message', 'notification', 'notification_read');
```

## 时区处理说明

本系统对时区处理进行了优化，确保在不同环境中正确处理时间：

1. **本地环境**：
   - 输入时间被视为北京时间
   - 添加Asia/Shanghai时区信息
   - 存储到数据库

2. **Render环境**：
   - 输入时间被视为北京时间
   - 添加Asia/Shanghai时区信息
   - 转换为UTC时间
   - 移除时区信息
   - 存储到数据库

3. **数据库查询**：
   - 使用`ensure_timezone_aware`函数处理时间
   - 在Render环境中，假设数据库时间为UTC
   - 在本地环境中，假设数据库时间为北京时间

这种处理方式确保了无论在哪种环境下，时间显示和比较都是准确的。 