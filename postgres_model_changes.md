# PostgreSQL 数据库模型更改总结

在将应用从 SQLite 迁移到 PostgreSQL 后，我们对 SQLAlchemy 模型进行了以下更新，以确保与 PostgreSQL 数据库表结构的兼容性：

## 通用更改

1. **时区处理**：
   - 移除了所有 `DateTime` 列上的 `timezone=True` 参数，因为 PostgreSQL 中的时间戳默认不带时区信息
   - 确保在应用层处理时区转换，而不是依赖数据库

2. **空值约束**：
   - 添加了 `nullable=False` 到必需字段，以匹配 PostgreSQL 表结构

3. **字符串长度**：
   - 调整了字符串字段的长度以匹配 PostgreSQL 表定义，例如：
     - `real_name` 从 `String(64)` 改为 `String(50)`
     - `college` 和 `major` 从 `String(64)` 改为 `String(100)`
     - `grade` 从 `String(10)` 改为 `String(20)`

## 表名更改

- `messages` → `message`
- `notifications` → `notification`
- `ai_chat_sessions` → `ai_chat_session`

## 字段更改

### User 模型
- `password_hash` 长度从 128 改为 256
- `last_login` 不再有默认值和 `onupdate` 触发器

### StudentInfo 模型
- 添加了 `qq` 字段
- 添加了 `has_selected_tags` 字段

### Tag 模型
- 将 `category` 字段替换为 `description` 字段，类型从 `String(64)` 改为 `Text`

### Activity 模型
- 添加了签到相关字段：`checkin_key`、`checkin_key_expires`、`checkin_enabled`
- 移除了 `min_participants` 字段
- 移除了 `poster_url` 字段
- 添加了 `is_featured` 字段
- `points` 默认值从 0 改为 10
- `type` 默认值从 'other' 改为 '其他'，长度从 20 改为 50

### Registration 模型
- 添加了 `check_in_time` 字段
- 添加了 `remark` 字段
- `status` 默认值从 'pending' 改为 'registered'

### PointsHistory 模型
- 将 `user_id` 字段替换为 `student_id`，引用 `student_info.id`
- `reason` 长度从 256 改为 200

### ActivityReview 模型
- 添加了 `content_quality`、`organization`、`facility`、`is_anonymous` 字段
- 将 `comment` 字段重命名为 `review`

### Announcement 模型
- 添加了 `updated_at` 和 `status` 字段

### ActivityCheckin 模型
- 将 `is_manual` 字段替换为 `status` 字段

### Message 模型
- 将 `recipient_id` 字段重命名为 `receiver_id`
- 将 `body` 字段重命名为 `content`
- 添加了 `subject` 字段
- 将 `timestamp` 字段重命名为 `created_at`

### Notification 模型
- 移除了 `user_id` 字段
- 添加了 `created_by`、`expiry_date`、`is_public` 字段
- 将 `type` 字段替换为 `is_important` 字段

### NotificationRead 模型
- 唯一约束名称从 `_user_notification_read_uc` 改为 `uq_notification_user`

### AIChatHistory 模型
- 将 `message` 和 `response` 字段替换为 `role` 和 `content` 字段

### AIChatSession 模型
- ID 类型从 `Integer` 改为 `String(255)`
- 移除了 `title` 字段

### AIUserPreferences 模型
- 将 `id` 字段移除，改用 `user_id` 作为主键
- 移除了 `interests` 和 `preferences` 字段
- 添加了 `enable_history` 和 `max_history_count` 字段

## 外键关系

- 更新了相关的外键关系以匹配表名更改
- 更新了 `messages_received` 关系，使用 `receiver_id` 而不是 `recipient_id`

## 类型处理

- 添加了 `str(self.password_hash)` 转换，确保密码验证函数正确处理 SQLAlchemy 列类型 