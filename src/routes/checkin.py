from flask import Blueprint, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from src.models import db, Activity, ActivityCheckin
from datetime import datetime

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

# 签到统计页面
@checkin_bp.route('/statistics/<int:activity_id>', methods=['GET'])
@login_required
def checkin_statistics(activity_id):
    activity = Activity.query.get(activity_id)
    if not activity:
        flash('活动不存在', 'danger')
        return redirect(url_for('admin.activities'))
    checkins = ActivityCheckin.query.filter_by(activity_id=activity_id).all()
    return render_template('admin/checkin_statistics.html', activity=activity, checkins=checkins)
