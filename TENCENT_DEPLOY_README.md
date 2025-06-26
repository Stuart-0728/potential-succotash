# 腾讯云Serverless部署说明

## 部署问题解决方案

我们的项目遇到了在Python 3.6环境下依赖版本不匹配的问题。以下是解决方案：

### 1. 已调整的配置

- 已将`requirements.txt`中的依赖版本降低至与Python 3.6兼容
- 已修改`bootstrap.sh`启动脚本，确保在启动前安装所需依赖
- 已修改`serverless.yml`配置，增加了超时时间并指定使用`bootstrap.sh`启动

### 2. 腾讯云部署配置参考

在腾讯云控制台配置时，请使用以下参数：

- **应用名**: cqnureg
- **环境**: 开发环境/生产环境
- **框架**: Flask应用
- **地域**: 广州/重庆（根据需要选择）
- **上传方式**: 代码仓库
- **运行环境**: Python 3.6
- **启动文件**: `bootstrap.sh`
- **内存**: 512MB
- **超时时间**: 60秒
- **环境变量**:
  - `FLASK_CONFIG`: production
  - `DATABASE_URL`: postgresql://cqnureg2_user:Pz8ZVfyLYOD22fkxp9w2XP7B9LsKAPqE@dpg-d1dugl7gi27c73er9p8g-a/cqnureg2
  - `ARK_API_KEY`: ccde7115-49bc-4977-9e17-e61075fa9eac

### 3. 注意事项

- 确保`bootstrap.sh`文件具有执行权限（chmod +x bootstrap.sh）
- 如果部署仍然失败，可以考虑以下选项：
  1. 尝试使用Python 3.7或更高版本的运行环境
  2. 进一步降低依赖版本要求
  3. 使用自定义层（Layer）提前安装依赖 