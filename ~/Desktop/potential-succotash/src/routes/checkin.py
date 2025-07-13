from flask import Blueprint, request, jsonify, flash, redirect, url_for, render_template, current_app
from flask_login import login_required, current_user
from src.models import db, Activity, ActivityCheckin, Registration, StudentInfo, PointsHistory
from datetime import datetime
import logging
from src import cache  # 导入缓存实例

logger = logging.getLogger(__name__)
checkin_bp = Blueprint('checkin', __name__, url_prefix='/checkin')

# 签到接口
@checkin_bp.route('/<int:activity_id>', methods=['POST'])
@login_required
def checkin(activity_id):
    activity = Activity.query.get(activity_id)
    if not activity:
        return jsonify({'success': False, 'msg': '活动不存在'})
    # 检查是否已签到
    existing_checkin = ActivityCheckin.query.filter_by(activity_id=activity_id, user_id=current_user.id).first()
    if existing_checkin:
        return jsonify({'success': False, 'msg': '已签到'})
    # 创建签到记录
    checkin_record = ActivityCheckin(
        activity_id=activity_id,
        user_id=current_user.id,
        checkin_time=datetime.utcnow(),
        status='checked_in'
    )
    db.session.add(checkin_record)
    db.session.commit()
    return jsonify({'success': True, 'msg': '签到成功'})

# 扫描二维码签到路由
@checkin_bp.route('/scan/<int:activity_id>/<string:checkin_key>')
@login_required
def scan_checkin(activity_id, checkin_key):
    try:
        # 检查活动是否存在
        activity = Activity.query.get_or_404(activity_id)
        
        # 优先从数据库验证密钥，如失败则从缓存验证
        valid_key = False
        if activity.checkin_key == checkin_key and activity.checkin_key_expires and activity.checkin_key_expires >= datetime.now():
            valid_key = True
        else:
            # 从缓存中获取签到密钥
            cache_key = f"checkin_key_{activity_id}"
            stored_key = cache.get(cache_key)
            if stored_key and stored_key == checkin_key:
                valid_key = True
        
        if not valid_key:
            flash('签到二维码无效或已过期', 'danger')
            return redirect(url_for('student.activities'))
        
        # 检查活动状态
        if activity.status != 'active':
            flash('该活动当前不可签到', 'warning')
            return redirect(url_for('student.activity_detail', id=activity_id))
        
        # 验证当前时间是否在活动时间范围内
        now = datetime.now()
        if now < activity.start_time or now > activity.end_time:
            flash('不在活动签到时间范围内', 'warning')
            return redirect(url_for('student.activity_detail', id=activity_id))
        
        # 检查用户是否已报名该活动
        registration = Registration.query.filter_by(
            user_id=current_user.id,
            activity_id=activity_id,
            status='registered'
        ).first()
        
        if not registration:
            flash('您尚未报名此活动，请先报名', 'warning')
            return redirect(url_for('student.activity_detail', id=activity_id))
        
        # 检查是否已签到
        if registration.check_in_time:
            flash('您已经签到过了', 'info')
            return redirect(url_for('student.activity_detail', id=activity_id))
        
        # 更新签到状态
        registration.check_in_time = now
        registration.status = 'checked_in'
        
        # 添加积分奖励
        points = activity.points or (20 if activity.is_featured else 10)  # 使用活动自定义积分或默认值
        student_info = StudentInfo.query.filter_by(user_id=current_user.id).first()
        if student_info:
            student_info.points = (student_info.points or 0) + points
            # 记录积分历史
            points_history = PointsHistory(
                student_id=student_info.id,
                points=points,
                reason=f"参与活动：{activity.title}",
                activity_id=activity.id
            )
            db.session.add(points_history)
        
        db.session.commit()
        flash(f'签到成功！获得 {points} 积分', 'success')
        
        # 重定向到活动详情页
        return redirect(url_for('student.activity_detail', id=activity_id))
        
    except Exception as e:
        logger.error(f"扫码签到失败: {e}")
        flash('签到失败，请重试', 'danger')
        return redirect(url_for('student.activities')) 