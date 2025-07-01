# Render 部署说明

本目录包含在 Render 平台部署应用所需的文件。

## 部署所需文件

1. `wsgi.py` - WSGI应用入口点
2. `Procfile` - 定义应用启动命令
3. `gunicorn_config.py` - Gunicorn配置文件
4. `build.sh` - 构建脚本，特别处理了numpy和pandas的安装

## 部署步骤

在 Render 平台部署时，请按照以下步骤操作：

1. 在 Render 上创建一个新的 Web Service
2. 连接 GitHub 仓库
3. 设置以下配置：
   - 名称：`cqnureg`（或您选择的名称）
   - 运行时环境：Python
   - 构建命令：`bash render_deploy/build.sh`
   - 启动命令：`cd render_deploy && gunicorn -c gunicorn_config.py wsgi:app`
   - 实例类型：根据需求选择（建议至少512MB内存）

4. 配置环境变量：
   - `FLASK_CONFIG` = `production`
   - `DATABASE_URL` = 您的PostgreSQL数据库连接URL
   - `ARK_API_KEY` = 您的API密钥（如果使用）

5. 点击"创建Web Service"按钮

## 备份与恢复

### 备份步骤

1. 保持此目录中的文件与主项目保持同步
2. 定期备份数据库（Render PostgreSQL）:
   ```bash
   pg_dump -Fc postgresql://username:password@host:port/database > backup_$(date +%Y%m%d).dump
   ```

3. 备份环境变量（手动记录或使用脚本导出）

### 恢复步骤

1. 重新部署应用（如果需要）
2. 恢复数据库：
   ```bash
   pg_restore -d postgresql://username:password@host:port/database backup.dump
   ```

3. 重新配置环境变量

## 注意事项

1. 确保数据库连接URL使用PostgreSQL格式，例如：
   ```
   postgresql://username:password@host:port/database
   ```

2. 如果需要手动部署，请执行以下命令：
   ```bash
   git push render main
   ```

3. Render会自动检测代码变动并重新部署应用 