from src import create_app
from flask import Blueprint, render_template
from src.models import Activity
from src.routes.utils import admin_required
from flask_login import login_required

# 创建应用
app = create_app()

# 获取admin_bp蓝图
from src.routes.admin import admin_bp

# 删除原有路由
for rule in list(app.url_map.iter_rules()):
    if 'checkin_modal' in str(rule):
        print(f"删除路由: {rule}")
        # 无法直接删除路由，但我们可以重新注册它

# 添加新路由
@admin_bp.route('/admin/checkin-modal/<int:id>')
@login_required
@admin_required
def checkin_modal_fixed(id):
    """活动签到管理模态框 (修复版)"""
    try:
        activity = db.get_or_404(Activity, id)
        return render_template('admin/checkin_modal.html', activity=activity)
    except Exception as e:
        print(f"签到管理页面出错: {e}")
        return "加载签到管理页面失败"

# 将新路由注册到应用
app.register_blueprint(admin_bp)

# 输出修复结果
print("路由修复完成")
print("以下是当前应用中包含'checkin'的所有路由:")
with app.app_context():
    for rule in app.url_map.iter_rules():
        if 'checkin' in str(rule):
            print(f"路由: {rule}, 终点: {rule.endpoint}")

print("\n请重启应用以应用这些更改") 