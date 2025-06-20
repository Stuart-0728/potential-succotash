from flask import Blueprint, request, jsonify, flash, redirect, url_for, render_template, current_app
from flask_login import login_required, current_user
from src.models import db, Activity, ActivityCheckin, Registration, StudentInfo, PointsHistory
from datetime import datetime, timezone, timedelta
import logging
from src.utils.time_helpers import get_beijing_time, localize_time, ensure_timezone_aware, normalize_datetime_for_db

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
        checkin_time=normalize_datetime_for_db(datetime.now()),  # 使用normalize_datetime_for_db函数处理
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
        
        # 验证签到密钥是否有效
        valid_key = False
        now = get_beijing_time()
        
        # 确保checkin_key_expires有时区信息
        expires_time = activity.checkin_key_expires
        if expires_time:
            expires_time = ensure_timezone_aware(expires_time)
        
        if activity.checkin_key == checkin_key and expires_time and expires_time >= now:
            valid_key = True
            
        if not valid_key:
            flash('签到二维码无效或已过期', 'danger')
            return redirect(url_for('student.activities'))
        
        # 检查活动状态
        if activity.status != 'active':
            flash('该活动当前不可签到', 'warning')
            return redirect(url_for('student.activity_detail', id=activity_id))
        
        # 检查是否手动开启了签到
        checkin_enabled = getattr(activity, 'checkin_enabled', False)
        logger.info(f"活动签到状态: 活动ID={activity_id}, 签到已手动开启={checkin_enabled}")
        
        # 如果没有手动开启签到，则验证当前时间是否在活动时间范围内
        if not checkin_enabled:
            # 确保活动时间有时区信息，并且都转换为北京时间进行比较
            start_time = ensure_timezone_aware(activity.start_time) if activity.start_time else now
            end_time = ensure_timezone_aware(activity.end_time) if activity.end_time else now + timedelta(hours=2)
                
            # 添加灵活度：允许活动开始前30分钟和结束后30分钟的签到
            start_time_buffer = start_time - timedelta(minutes=30)
            end_time_buffer = end_time + timedelta(minutes=30)
        
            logger.info(f"签到时间检查: 当前北京时间={now}, 活动开始时间={start_time}, 活动结束时间={end_time}")
            
            if now < start_time_buffer or now > end_time_buffer:
                flash('不在活动签到时间范围内', 'warning')
                return redirect(url_for('student.activity_detail', id=activity_id))
        else:
            logger.info(f"签到时间检查已忽略: 活动ID={activity_id}，已手动开启签到")
        
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
        registration.check_in_time = normalize_datetime_for_db(datetime.now())  # 使用normalize_datetime_for_db函数处理
        registration.status = 'attended'
        
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
