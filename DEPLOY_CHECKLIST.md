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