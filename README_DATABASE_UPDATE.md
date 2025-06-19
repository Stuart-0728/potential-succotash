# 数据库更新说明

本次更新包含AI聊天历史记录相关功能的增强，主要改进有：

1. 添加了清除所有聊天历史记录的功能
2. 优化了数据库索引以提高查询和删除操作性能
3. 增加了用户级别的聊天历史管理

## 数据库更新步骤

### 本地开发环境 (SQLite)

本地SQLite数据库不需要额外操作，应用程序启动时会自动创建必要的表和索引。

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