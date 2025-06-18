from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from src.models import db, Tag, StudentInfo, StudentInterestTag
import logging

logger = logging.getLogger(__name__)

select_tags_bp = Blueprint('select_tags', __name__, url_prefix='/select-tags')

@select_tags_bp.route('/', methods=['GET', 'POST'])
@login_required
def select_tags():
    """学生选择兴趣标签页面"""
    try:
        # 获取学生信息
        student_info = StudentInfo.query.filter_by(user_id=current_user.id).first()
        if not student_info:
            flash('请先完善个人信息', 'warning')
            return redirect(url_for('student.edit_profile'))
        
        # 获取所有标签
        all_tags = Tag.query.order_by(Tag.name).all()
        
        # 获取学生已选标签
        selected_tag_ids = [tag.id for tag in student_info.tags] if student_info.tags else []
        
        if request.method == 'POST':
            # 获取提交的标签ID列表
            tag_ids = request.form.getlist('tags')
            
            # 清空现有标签关联
            StudentInterestTag.query.filter_by(student_id=student_info.id).delete()
            
            # 添加新的标签关联
            if tag_ids:
                for tag_id in tag_ids:
                    student_tag = StudentInterestTag(student_id=student_info.id, tag_id=int(tag_id))
                    db.session.add(student_tag)
            
            # 更新学生已选择标签状态
            student_info.has_selected_tags = True
            db.session.commit()
            
            flash('兴趣标签保存成功！', 'success')
            
            # 如果是首次登录选择标签，重定向到学生仪表盘
            if request.args.get('first_login'):
                return redirect(url_for('student.dashboard'))
            
            # 否则重定向到个人资料页
            return redirect(url_for('student.profile'))
        
        # 判断是否首次登录
        first_login = request.args.get('first_login', 'false') == 'true'
        
        return render_template('select_tags.html', 
                              tags=all_tags, 
                              selected_tag_ids=selected_tag_ids,
                              first_login=first_login)
    
    except Exception as e:
        logger.error(f"选择标签时出错: {e}")
        db.session.rollback()
        flash('选择标签时发生错误，请稍后重试', 'danger')
        return redirect(url_for('student.dashboard')) 