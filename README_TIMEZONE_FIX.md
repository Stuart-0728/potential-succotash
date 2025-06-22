# 时区问题修复指南

本文档提供了修复Render部署环境中时区问题的详细说明。

## 问题描述

在Render部署环境中，PostgreSQL数据库和应用程序之间存在时区不一致的问题，导致活动时间显示比实际设置时间少8小时。这是因为：

1. PostgreSQL数据库默认使用UTC时区
2. 应用程序需要显示北京时间（UTC+8）
3. 时区转换处理不当导致时间显示错误

## 解决方案

### 1. 修改时间处理工具函数

我们对`src/utils/time_helpers.py`文件进行了以下修改：

- 添加了`display_datetime`函数，用于正确显示北京时间
- 优化了`is_render_environment`函数，确保正确检测Render环境
- 完善了`normalize_datetime_for_db`函数，确保存储到数据库的时间格式正确

### 2. 在模板中使用display_datetime函数

将所有模板中直接调用`strftime`的地方替换为`display_datetime`函数：

```html
<!-- 修改前 -->
{{ activity.start_time.strftime('%Y-%m-%d %H:%M') }}

<!-- 修改后 -->
{{ display_datetime(activity.start_time) }}
```

### 3. 在应用初始化时注册全局模板函数

在`src/__init__.py`中添加：

```python
# 添加全局模板函数
app.jinja_env.globals.update(display_datetime=display_datetime)
```

### 4. 修复数据库中的时区问题

创建了`fix_render_timezone.py`脚本，用于修复PostgreSQL数据库中的时区问题：

- 设置数据库时区为UTC
- 修复活动表中的时间字段
- 修复通知表中的时间字段
- 修复报名表中的时间字段
- 修复其他相关表中的时间字段

## 部署步骤

1. 将代码推送到GitHub仓库
   ```bash
   git add .
   git commit -m "修复时区问题和站内信显示问题"
   git push origin main
   ```

2. 在Render控制台中执行以下操作：
   - 进入Web Service设置
   - 确保环境变量`RENDER=true`已设置
   - 点击"Manual Deploy"按钮，选择"Deploy latest commit"

3. 部署完成后，通过SSH或Render Shell运行时区修复脚本：
   ```bash
   python fix_render_timezone.py
   ```

4. 验证修复结果：
   - 检查活动时间是否正确显示
   - 检查通知时间是否正确显示
   - 检查报名和签到时间是否正确显示

## 注意事项

1. 确保所有与时间相关的操作都使用`display_datetime`函数进行显示
2. 在创建或编辑活动时，表单中的`LocalizedDateTimeField`类已经正确处理了时区转换
3. 如果未来需要添加新的时间相关功能，请确保遵循相同的时区处理模式

## 故障排除

如果时区问题仍然存在，请检查：

1. 环境变量`RENDER=true`是否正确设置
2. 数据库时区设置是否为UTC
3. 应用是否正确使用`display_datetime`函数显示时间
4. 数据库中的时间数据是否已正确转换

如有任何问题，请联系系统管理员。 