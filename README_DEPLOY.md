# 部署指南

本文档提供了在云平台部署应用的详细指南。

## 目录

- [Render部署](#render部署)
- [数据库备份和恢复](#数据库备份和恢复)
- [常见问题解决](#常见问题解决)

## Render部署

Render使用传统的Web服务方式部署应用。

### 部署所需文件

所有必需文件都在`render_deploy`目录中：
1. `wsgi.py` - WSGI应用入口点
2. `Procfile` - 定义应用启动命令
3. `gunicorn_config.py` - Gunicorn配置文件

### 部署步骤

1. 在 Render 上创建一个新的 Web Service
2. 连接您的 GitHub 仓库
3. 设置以下配置：
   - 名称：`cqnureg`（或您选择的名称）
   - 运行时环境：Python 3.7+
   - 构建命令：`pip install -r requirements.txt`
   - 启动命令：`gunicorn -c gunicorn_config.py wsgi:app`
   - 实例类型：至少512MB内存

4. 配置环境变量：
   - `FLASK_CONFIG` = `production`
   - `DATABASE_URL` = 您的PostgreSQL数据库连接URL
   - `ARK_API_KEY` = 您的API密钥（如果使用）

5. 点击"创建Web Service"按钮

### 优点和限制

**优点：**
- 简单直接的部署流程
- 内置PostgreSQL数据库服务
- 持久文件系统
- 稳定的长时间运行性能

**限制：**
- 空闲时仍会计费
- 需要配置最小实例数
- 冷启动时间较长

## 数据库备份和恢复

定期备份数据库是必要的。

### PostgreSQL数据库备份

```bash
# 备份
pg_dump -Fc "postgresql://username:password@host:port/database" > backup_$(date +%Y%m%d).dump

# 恢复
pg_restore -d "postgresql://username:password@host:port/database" backup.dump
```

### 注意事项

- 定期执行备份（建议每天一次）
- 保留多个备份版本（最少7天）
- 将备份存储在不同的物理位置
- 定期测试恢复过程

## 常见问题解决

### 依赖安装失败

**问题：** `ERROR: No matching distribution found for Flask>=2.3.3`

**解决方案：** 
- 修改requirements.txt使用兼容的版本：
  ```
  Flask>=2.0.0,<2.3.0
  ```

### 部署超时

**问题：** 部署过程中出现超时错误

**解决方案：**
- 减少依赖包大小
- 使用bootstrap脚本分阶段安装

### 数据库连接问题

**问题：** 应用无法连接数据库

**解决方案：**
- 检查数据库连接字符串格式
- 确认网络连接和防火墙设置
- 验证数据库用户权限 