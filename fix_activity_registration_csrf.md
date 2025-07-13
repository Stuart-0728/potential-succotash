# 活动报名CSRF问题修复总结

## 问题描述

学生在活动详情页面尝试报名活动时出现错误：

```
flask_wtf.csrf - INFO - The CSRF token is missing.
```

这导致报名请求被拒绝，返回HTTP 400错误，用户无法报名活动。

## 问题原因

1. 在活动详情页模板(`student/activity_detail.html`)中，报名表单缺少CSRF令牌字段
2. 路由函数中已经配置了CSRF验证，但模板中没有提供对应的令牌
3. 重定向链接不正确，使用了错误的URL命名空间

## 问题位置

* 文件: `src/templates/student/activity_detail.html`
* 路由函数: `src/routes/student.py` 中的 `register_activity` 和 `cancel_registration`

## 解决方案

1. 在所有表单中添加CSRF令牌字段：

```html
<form method="post" action="{{ url_for('student.register_activity', id=activity.id) }}">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    <button type="submit" class="btn btn-primary">
        <i class="fas fa-user-plus me-1"></i>立即报名
    </button>
</form>
```

2. 修复路由函数中的重定向URL：

将所有 `return redirect(url_for('main.activity_detail', activity_id=id))` 
修改为 `return redirect(url_for('student.activity_detail', id=id))`

## 影响和测试

修复后：
- 学生可以正常报名活动
- 学生可以取消已报名的活动
- 修复了URL重定向问题，确保用户操作后能回到正确的页面

## 预防措施

1. 对所有POST表单添加CSRF保护
2. 建立统一的表单验证和处理机制
3. 创建URL命名空间的映射文档，避免错误引用路由名称 