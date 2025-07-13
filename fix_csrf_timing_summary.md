# CSRF豁免配置执行顺序修复

## 问题描述

应用在Render平台上部署时遇到以下错误：

```
File "/opt/render/project/src/src/__init__.py", line 96, in create_app
    app.view_functions[education_bp.name + '.gemini_api']._csrf_exempt = True
KeyError: 'education.gemini_api'
```

## 原因分析

这是一个执行顺序问题：

1. 代码尝试在蓝图注册之前访问和修改 `education.gemini_api` 路由
2. 在 Flask 应用中，蓝图中的路由只有在调用 `app.register_blueprint(education_bp)` 后才会被注册到 `app.view_functions` 字典中
3. 因此在蓝图注册之前，尝试访问 `app.view_functions[education_bp.name + '.gemini_api']` 会导致 `KeyError`

## 修复内容

1. **移动代码位置**：将 CSRF 豁免配置代码从蓝图注册前移动到蓝图注册后执行
   ```python
   # 先注册蓝图
   register_blueprints(app)
   
   # 然后添加CSRF豁免
   with app.app_context():
       csrf.exempt('education.gemini_api')
       app.logger.info('已为education.gemini_api路由添加CSRF豁免')
   ```

2. **使用标准API**：使用 Flask-WTF 提供的 `csrf.exempt()` 方法替代直接设置内部属性 `_csrf_exempt`，这是更安全、更标准的做法
   ```python
   # 不再使用：
   # app.view_functions[education_bp.name + '.gemini_api']._csrf_exempt = True
   
   # 而是使用标准API：
   csrf.exempt('education.gemini_api')
   ```

## 关于执行顺序的注意事项

在 Flask 应用中，遵循正确的执行顺序非常重要：

1. 创建应用实例
2. 加载配置
3. 初始化扩展
4. 注册模型
5. 注册蓝图
6. 进行蓝图相关的配置（如CSRF豁免）
7. 注册错误处理、模板函数等

这个顺序确保了各组件之间的依赖关系得到正确处理。 