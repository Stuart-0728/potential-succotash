from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from src.models import db, Tag, Activity, activity_tags

tag_bp = Blueprint('tag', __name__, url_prefix='/tags')

# 标签管理页面
@tag_bp.route('/', methods=['GET'])
@login_required
def tag_list():
    tags = Tag.query.all()
    return render_template('admin/tags.html', tags=tags)

# 新建标签
@tag_bp.route('/create', methods=['POST'])
@login_required
def create_tag():
    name = request.form.get('name')
    desc = request.form.get('description')
    if not name:
        flash('标签名不能为空', 'danger')
        return redirect(url_for('tag.tag_list'))
    if Tag.query.filter_by(name=name).first():
        flash('标签已存在', 'warning')
        return redirect(url_for('tag.tag_list'))
    tag = Tag(name=name, description=desc)
    db.session.add(tag)
    db.session.commit()
    flash('标签创建成功', 'success')
    return redirect(url_for('tag.tag_list'))

# 删除标签
@tag_bp.route('/delete/<int:tag_id>', methods=['POST'])
@login_required
def delete_tag(tag_id):
    tag = Tag.query.get_or_404(tag_id)
    db.session.delete(tag)
    db.session.commit()
    flash('标签已删除', 'success')
    return redirect(url_for('tag.tag_list'))

# 活动打标签（AJAX接口）
@tag_bp.route('/assign', methods=['POST'])
@login_required
def assign_tag():
    activity_id = request.form.get('activity_id')
    tag_ids = request.form.getlist('tag_ids')
    activity = Activity.query.get(activity_id)
    if not activity:
        return jsonify({'success': False, 'msg': '活动不存在'})
    # 清空原有标签
    activity.tags = []
    # 添加新标签
    if tag_ids:
        tags = Tag.query.filter(Tag.id.in_(tag_ids)).all()
        activity.tags = tags
    db.session.commit()
    return jsonify({'success': True})
