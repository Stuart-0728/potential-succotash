# 部署检查清单

## 通用检查项

- [ ] 确认项目中没有敏感信息（如密码、API密钥）硬编码
- [ ] 确认所有依赖都已列在 `requirements.txt` 中
- [ ] 检查数据库URL配置是否正确
- [ ] 确认应用在本地可以正常启动

## Render部署检查项

- [ ] 确认 `wsgi.py` 文件存在且正确
- [ ] 确认 `Procfile` 文件存在且包含正确的启动命令
- [ ] 确认 `gunicorn_config.py` 配置正确
- [ ] 确保环境变量在Render平台上正确设置

## 腾讯云Serverless部署检查项

- [ ] 确认 `app.py` 文件存在且包含 `main_handler` 函数
- [ ] 确认 `bootstrap.sh` 文件存在且有执行权限
- [ ] 确认 `serverless.yml` 配置正确
- [ ] 配置环境变量在腾讯云平台上正确设置

## 腾讯云Serverless部署检查清单

## 准备工作

1. 确认代码已提交到GitHub仓库
   - [x] 已修改requirements.txt，降低依赖版本适配Python 3.6
   - [x] 已添加bootstrap.sh脚本并设置可执行权限
   - [x] 已添加app.py入口文件
   - [x] 已添加serverless.yml配置文件
   - [x] 已将所有文件推送到GitHub

2. 环境变量检查
   - [ ] TENCENT_SECRET_ID 设置正确
   - [ ] TENCENT_SECRET_KEY 设置正确
   - [ ] TENCENT_APP_ID 设置正确

## 常见部署问题及解决方案

### 1. 依赖安装失败

**错误信息**：`ERROR: No matching distribution found for Flask>=2.3.3`

**解决方案**：
- 已修改requirements.txt，降低Flask及其他依赖版本到Python 3.6兼容的版本
- 确保所有依赖都设置了较低的、与Python 3.6兼容的版本上限

### 2. 权限错误

**错误信息**：`secretId/secretKey/token is empty`

**解决方案**：
- 在腾讯云控制台重新授权访问凭证
- 确认API密钥有效且未过期
- 在腾讯云Serverless控制台手动配置密钥

### 3. 启动脚本问题

**确认**：
- bootstrap.sh有可执行权限
- bootstrap.sh中的命令正确（包括pip安装和应用启动）
- bootstrap.sh中包含错误处理机制

### 4. 配置文件正确性

**确认serverless.yml包含**：
- 正确的环境变量设置
- 适当的超时时间（至少60秒）
- 正确的内存设置（至少512MB）
- 正确的Python运行时版本（Python3.6）
- 正确的启动命令和引导脚本配置

## 部署后检查项

- [ ] 访问应用首页，确认正常加载
- [ ] 测试登录功能
- [ ] 测试数据库读写功能
- [ ] 确认静态文件（CSS、JS）正常加载
- [ ] 测试文件上传功能
- [ ] 检查应用日志，确保没有错误

## 资源清理

如果需要删除部署，请执行：
```bash
# 使用腾讯云CLI
tccli scf DeleteFunction --region ap-chongqing --FunctionName cqnureg

# 或在控制台删除服务
``` 