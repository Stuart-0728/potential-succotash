# Render 环境变量配置指南

本指南将帮助您在 Render 上配置双数据库环境变量，以实现主数据库（Render PostgreSQL）和备份数据库（ClawCloud）的配置。

## 必需的环境变量

### 1. 主数据库配置（Render PostgreSQL）

```bash
# 主数据库URL - Render会自动提供
DATABASE_URL=postgresql://username:password@hostname:port/database_name

# 或者单独配置（如果需要）
RENDER_DATABASE_URL=postgresql://username:password@hostname:port/database_name
```

### 2. 备份数据库配置（ClawCloud）

```bash
# 备份数据库URL - 您的ClawCloud数据库连接字符串
BACKUP_DATABASE_URL=postgresql://username:password@hostname:port/database_name

# 或者使用别名
CLAWCLOUD_DATABASE_URL=postgresql://username:password@hostname:port/database_name
```

### 3. 应用基础配置

```bash
# Flask密钥（必需）
SECRET_KEY=your-very-secure-secret-key-here

# 密码盐值
SECURITY_PASSWORD_SALT=your-password-salt-here

# 应用名称
APP_NAME=重庆师范大学师能素质协会

# 时区配置
TIMEZONE_NAME=Asia/Shanghai
APP_TIMEZONE=Asia/Shanghai
```

### 4. 数据库连接优化

```bash
# 数据库连接超时（秒）
DB_CONNECT_TIMEOUT=8

# SQLAlchemy回显（生产环境建议设为false）
SQLALCHEMY_ECHO=false
```

### 5. 同步配置

```bash
# 自动同步间隔（小时）
SYNC_INTERVAL_HOURS=6

# 是否在启动时立即同步
IMMEDIATE_SYNC=false
```

### 6. AI功能配置（可选）

```bash
# Google Gemini API密钥
GEMINI_API_KEY=your-gemini-api-key

# AI模型API URL
AI_MODEL_API_URL=https://generativelanguage.googleapis.com/

# 火山引擎API配置（可选）
VOLCANO_API_KEY=your-volcano-api-key
VOLCANO_API_URL=https://ark.cn-beijing.volces.com/api/v3/chat/completions
```

### 7. 缓存和限流配置

```bash
# 缓存超时时间（秒）
CACHE_TIMEOUT=300

# 日志配置
LOG_BACKUP_COUNT=10
LOG_MAX_BYTES=10485760

# 分页配置
ITEMS_PER_PAGE=10
```

## Render 配置步骤

### 1. 在 Render Dashboard 中配置

1. 登录 [Render Dashboard](https://dashboard.render.com)
2. 选择您的 Web Service
3. 点击 "Environment" 标签
4. 添加上述环境变量

### 2. 数据库配置

#### 主数据库（Render PostgreSQL）
1. 在 Render 中创建 PostgreSQL 数据库
2. Render 会自动设置 `DATABASE_URL` 环境变量
3. 确保您的 Web Service 连接到此数据库

#### 备份数据库（ClawCloud）
1. 获取您的 ClawCloud PostgreSQL 连接字符串
2. 在 Render 环境变量中设置 `BACKUP_DATABASE_URL`

### 3. 环境变量示例

```bash
# 主数据库（Render自动提供）
DATABASE_URL=postgresql://user:pass@dpg-xxxxx-a.oregon-postgres.render.com/dbname

# 备份数据库（ClawCloud）
BACKUP_DATABASE_URL=postgresql://user:pass@your-clawcloud-host:5432/dbname

# 应用配置
SECRET_KEY=super-secret-key-change-this-in-production
SECURITY_PASSWORD_SALT=your-unique-salt
APP_NAME=重庆师范大学师能素质协会
TIMEZONE_NAME=Asia/Shanghai

# 数据库优化
DB_CONNECT_TIMEOUT=8
SYNC_INTERVAL_HOURS=6

# AI功能（可选）
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

## 双数据库工作原理

### 主数据库（Render PostgreSQL）
- 用于日常操作
- 更低的延迟（与应用在同一区域）
- 自动备份和维护

### 备份数据库（ClawCloud）
- 用作数据备份
- 定期从主数据库同步数据
- 在主数据库不可用时可作为故障转移

### 自动同步
- 每6小时自动将主数据库备份到ClawCloud
- 可通过管理面板手动触发同步
- 支持从ClawCloud恢复到主数据库

## 部署后验证

### 1. 检查数据库连接
访问 `/admin/database-status` 页面检查：
- 主数据库连接状态
- 备份数据库连接状态
- 连接延迟

### 2. 测试同步功能
在管理面板中：
- 执行"备份到ClawCloud"
- 检查同步日志
- 验证数据一致性

### 3. 监控日志
检查应用日志中的数据库连接信息：
```
使用主数据库: postgresql://...
双数据库已启用
```

## 故障排除

### 常见问题

1. **连接超时**
   - 检查 `DB_CONNECT_TIMEOUT` 设置
   - 验证数据库URL格式
   - 确认网络连接

2. **同步失败**
   - 检查两个数据库的连接状态
   - 验证权限设置
   - 查看同步日志

3. **性能问题**
   - 调整连接池大小
   - 检查数据库延迟
   - 优化查询

### 日志查看
在 Render 中查看应用日志：
1. 进入 Web Service
2. 点击 "Logs" 标签
3. 查找数据库相关的日志信息

## 安全注意事项

1. **密钥管理**
   - 使用强密码和密钥
   - 定期更换敏感信息
   - 不要在代码中硬编码密钥

2. **数据库安全**
   - 限制数据库访问权限
   - 使用SSL连接
   - 定期备份数据

3. **环境隔离**
   - 生产环境和开发环境使用不同的数据库
   - 不要在生产环境中启用调试模式

## 性能优化建议

1. **连接池优化**
   - 根据应用负载调整 `pool_size`
   - 设置合适的 `pool_timeout`

2. **同步策略**
   - 根据数据重要性调整同步频率
   - 在低峰时段执行同步

3. **监控**
   - 定期检查数据库状态
   - 监控连接延迟
   - 设置告警机制

## 快速部署检查清单

### 部署前
- [ ] 清理项目文件：`python cleanup_project.py`
- [ ] 检查 requirements.txt
- [ ] 确认 Procfile 配置
- [ ] 设置环境变量

### 部署后
- [ ] 访问 `/admin/database-status` 检查数据库
- [ ] 创建管理员账户：`python create_admin.py`
- [ ] 测试基本功能
- [ ] 设置自动同步（如需要）

## 联系支持

如果遇到问题，请：
1. 检查 Render 文档
2. 查看应用日志
3. 联系技术支持

---

**注意**: 请确保在生产环境中使用强密钥和安全的数据库连接。定期备份数据并测试恢复流程。
