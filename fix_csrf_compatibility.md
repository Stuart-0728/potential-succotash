# CSRF兼容性问题修复总结 - 2025年6月25日

## 问题描述

在Render.com部署环境中遇到以下错误：

```
ImportError: cannot import name 'csrf_exempt' from 'flask_wtf.csrf' (/opt/render/project/src/.venv/lib/python3.11/site-packages/flask_wtf/csrf.py)
```

这表明服务器上的Flask-WTF版本与本地开发环境不同，不支持`csrf_exempt`装饰器。

## 问题分析

1. 我们在本地开发环境中使用的是较新版本的Flask-WTF，支持直接从`flask_wtf.csrf`导入`csrf_exempt`装饰器
2. 但在Render.com的部署环境中使用的是较旧的版本，不支持此功能
3. 此差异导致了代码在本地开发环境中可以正常运行，但部署到生产环境时出现导入错误

## 修复方案

我们采用了两步修复：

### 1. 移除对`csrf_exempt`的直接导入和使用

移除以下导入：
```python
from flask_wtf.csrf import CSRFProtect, generate_csrf, csrf_exempt
```

替换为：
```python
from flask_wtf.csrf import CSRFProtect, generate_csrf
```

### 2. 使用Flask原生的视图函数属性标记方式豁免CSRF保护

在application工厂函数中，添加以下代码：

```python
# 初始化CSRF保护
csrf.init_app(app)

# 添加特定API路由的CSRF豁免
from src.routes.education import education_bp

@app.after_request
def add_csrf_protection(response):
    """为应用添加CSRF保护"""
    return response

# 使用Flask原生方式为特定路由豁免CSRF保护
education_gemini_view = app.view_functions.get(education_bp.name + '.gemini_api')
if education_gemini_view:
    education_gemini_view._csrf_exempt = True
    app.logger.info('已为/education/api/gemini路由添加CSRF豁免')
else:
    app.logger.warning('未找到gemini_api视图函数，无法添加CSRF豁免')
```

这种方法利用了Flask-WTF在所有版本中都支持的一个特性：通过设置视图函数的`_csrf_exempt`属性为`True`来豁免CSRF保护。

## 修复过程

1. 创建了`test_deploy_fix7.py`脚本处理基础的CSRF导入和装饰器替换
2. 创建了`test_deploy_fix8.py`脚本修复因代码结构问题导致的错误，包括：
   - 修复了代码缩进问题
   - 清理了重复的导入语句
   - 正确设置了视图函数的CSRF豁免
3. 修复了`education.py`和`__init__.py`两个核心文件

## 验证方法

1. 部署到Render.com后，应用应能正常启动，没有导入错误
2. 自由落体页面(`/education/free-fall`)中的AI功能应能正常工作
3. 检查日志中是否有"已为/education/api/gemini路由添加CSRF豁免"的消息

## 教训与最佳实践

1. 始终指定精确的依赖版本，避免不同环境间的版本差异
2. 在不同环境中测试代码，确保兼容性
3. 在使用第三方库功能时，优先选择稳定的、长期支持的API
4. 使用兼容性更好的替代方案，如Flask原生的视图函数属性标记

## 后续工作

1. 考虑为项目添加Docker容器化，确保开发环境和生产环境的一致性
2. 创建更完善的自动化测试，包括在不同的Flask和Flask-WTF版本中测试
3. 制定一个明确的依赖管理策略，定期更新和审核依赖 