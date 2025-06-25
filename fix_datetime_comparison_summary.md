# 时间比较问题修复总结

## 问题描述

在学生活动详情页面(`student/activity_detail.html`)中，我们发现了一个时区比较错误：

```
TypeError: can't compare offset-naive and offset-aware datetimes
```

这个错误发生在模板直接比较带时区信息(offset-aware)和不带时区信息(offset-naive)的datetime对象时：

```python
{% if activity.start_time > now %}
```

## 问题原因

在Python中，当比较带时区信息的datetime对象与不带时区信息的datetime对象时，会引发TypeError错误，因为它们在概念上是不可比较的。

这是因为:
1. 一个datetime有明确的时区信息（例如UTC+8）
2. 另一个datetime没有时区信息（"naive"时间）

## 解决方案

1. 在`src/utils/time_helpers.py`中添加了新的安全比较函数：
   - `safe_greater_than_equal`: 安全比较datetime1 >= datetime2
   - `safe_less_than_equal`: 安全比较datetime1 <= datetime2

2. 修改模板中的直接比较为使用安全比较函数：
   - `activity.start_time > now` → `safe_greater_than(activity.start_time, now)`
   - `activity.registration_deadline >= now` → `safe_greater_than_equal(activity.registration_deadline, now)`
   - `now >= activity.start_time and now <= activity.end_time` → `safe_greater_than_equal(now, activity.start_time) and safe_less_than_equal(now, activity.end_time)`

3. 在路由函数中将新的安全比较函数传递给模板：
   ```python
   return render_template('student/activity_detail.html',
                          # 其他参数...
                          safe_less_than=safe_less_than,
                          safe_greater_than=safe_greater_than,
                          safe_greater_than_equal=safe_greater_than_equal,
                          safe_less_than_equal=safe_less_than_equal)
   ```

这些安全比较函数确保在比较时间前，先将两个datetime对象都转换为带时区信息的对象，避免TypeError错误。

## 测试结果

修复后，活动详情页面可以正确加载，不再出现时区比较错误。用户可以在活动页面中根据时间正确查看报名状态、签到按钮等功能。 