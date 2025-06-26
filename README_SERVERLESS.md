# 腾讯云 Serverless 部署说明

本项目可以部署到腾讯云 Serverless 平台。以下是部署步骤和所需文件说明。

## 部署所需文件

1. `app.py` - Flask应用入口点，包含腾讯云Serverless函数入口
2. `bootstrap.sh` - 启动脚本
3. `serverless.yml` - Serverless Framework配置文件

## 部署步骤

### 方法一：使用腾讯云控制台

1. 登录腾讯云控制台
2. 进入Serverless应用中心
3. 创建新应用，选择Flask框架
4. 配置以下参数：
   - 应用名：`cqnureg`（或您选择的名称）
   - 环境：开发环境/生产环境
   - 地域：广州（或您选择的地域）
   - 上传方式：代码仓库（GitHub）
   - 运行环境：Python 3.6
   - 启动文件：`bootstrap.sh`
   - 内存：512MB
   - 超时时间：30秒
   - 环境变量：
     - `FLASK_CONFIG` = `production`
     - `DATABASE_URL` = 您的PostgreSQL数据库连接URL
     - `ARK_API_KEY` = 您的API密钥（如果使用）

### 方法二：使用Serverless Framework

1. 安装Serverless Framework：
   ```bash
   npm install -g serverless
   ```

2. 安装腾讯云相关插件：
   ```bash
   npm install -g serverless-tencent
   ```

3. 配置腾讯云凭证：
   ```bash
   serverless config credentials --provider tencent --secretId <您的SecretId> --secretKey <您的SecretKey>
   ```

4. 部署应用：
   ```bash
   serverless deploy
   ```

## 注意事项

1. 确保数据库连接支持从外部访问，或者使用腾讯云提供的数据库服务
2. 对于静态文件和用户上传文件的处理，建议使用腾讯云对象存储COS
3. 在腾讯云Serverless环境中，本地文件系统是临时性的，请勿存储持久化数据
4. 如果应用需要处理大量请求或长时间运行的任务，建议增加内存配置

## 本地测试

在部署前可以在本地测试应用：

```bash
# 安装依赖
pip install -r requirements.txt

# 运行应用
python app.py
```

## 日志查看

部署后可以通过腾讯云控制台查看应用日志，或使用Serverless Framework：

```bash
serverless logs -f cqnureg
``` 