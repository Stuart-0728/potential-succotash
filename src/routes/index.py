"""
修复问题记录

1. 管理员删除通知时显示404错误
   - 原因：在notifications.html模板中使用了不存在的form.csrf_token变量
   - 解决方案：修改为使用正确的csrf_token()函数生成CSRF令牌

2. 首页海报与活动详情海报不符
   - 原因：首页和活动详情页使用了不同的备用海报逻辑
   - 解决方案：统一两处的备用海报逻辑，都使用banner1.jpg、banner2.jpg和banner3.jpg
   - 增强：在活动详情页中添加了根据活动ID查找匹配海报文件的功能

3. 编辑活动时出错"'int' object has no attribute '_sa_instance_state'"
   - 原因：在edit_activity函数中错误地尝试将活动ID转换为整数并使用
   - 解决方案：修改为使用handle_poster_upload函数处理文件上传，该函数已经能正确处理活动ID

4. 学生注册时出现"No module named 'email_validator'"错误
   - 原因：缺少email_validator库
   - 解决方案：在requirements.txt中添加email_validator>=2.0.0依赖并安装

5. 海报上传后不能正常显示
   - 原因：上传的海报文件名与数据库中记录的不一致
   - 解决方案：在活动详情页中添加了根据活动ID查找匹配海报文件的功能，即使数据库中记录的具体文件名不一致，也能找到正确的海报文件
""" 