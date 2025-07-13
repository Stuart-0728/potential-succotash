#!/usr/bin/env python3
"""
站内信调试工具
用于检查和修复站内信问题
"""

import os
import sys
import logging
from datetime import datetime

# 设置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 将当前目录添加到模块搜索路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def check_messages():
    """检查站内信状态"""
    try:
        # 导入必要的模块
        from src import create_app
        from src.models import db, User, Role, Message, StudentInfo
        
        # 创建应用上下文
        app = create_app()
        with app.app_context():
            logger.info("=== 站内信系统检查 ===")
            
            # 1. 检查角色情况
            admin_role = db.session.execute(db.select(Role).filter_by(name='Admin')).scalar_one_or_none()
            student_role = db.session.execute(db.select(Role).filter_by(name='Student')).scalar_one_or_none()
            
            if not admin_role:
                logger.error("管理员角色不存在!")
                return False
            
            if not student_role:
                logger.error("学生角色不存在!")
                return False
            
            # 2. 检查用户情况
            admins = db.session.execute(db.select(User).filter_by(role_id=admin_role.id)).scalars().all()
            students = db.session.execute(db.select(User).filter_by(role_id=student_role.id)).scalars().all()
            
            logger.info(f"管理员: {len(admins)}人")
            for admin in admins:
                logger.info(f"  - {admin.username} (ID: {admin.id})")
            
            logger.info(f"学生: {len(students)}人")
            for student in students[:5]:  # 只显示前5个学生
                student_info = db.session.execute(db.select(StudentInfo).filter_by(user_id=student.id)).scalar_one_or_none()
                real_name = student_info.real_name if student_info else "未知"
                logger.info(f"  - {student.username} (ID: {student.id}, 姓名: {real_name})")
            
            if len(students) > 5:
                logger.info(f"  ... 等{len(students)-5}人")
            
            # 3. 检查消息情况
            messages = db.session.execute(db.select(Message)).scalars().all()
            logger.info(f"总消息数: {len(messages)}条")
            
            # 4. 检查消息发送情况
            admin_sent = Message.query.filter(Message.sender_id.in_([a.id for a in admins])).all()
            logger.info(f"管理员发送消息: {len(admin_sent)}条")
            
            # 5. 检查消息接收情况
            student_received = Message.query.filter(Message.receiver_id.in_([s.id for s in students])).all()
            logger.info(f"学生接收消息: {len(student_received)}条")
            
            # 6. 检查未读消息
            unread_messages = db.session.execute(db.select(Message).filter_by(is_read=False)).scalars().all()
            logger.info(f"未读消息: {len(unread_messages)}条")
            
            # 7. 输出最近消息
            recent_messages = Message.query.order_by(Message.created_at.desc()).limit(5).all()
            logger.info("最近5条消息:")
            for msg in recent_messages:
                sender = db.session.get(User, msg.sender_id)
                receiver = db.session.get(User, msg.receiver_id)
                logger.info(f"  - 发送于: {msg.created_at.strftime('%Y-%m-%d %H:%M')}")
                logger.info(f"    标题: {msg.subject}")
                logger.info(f"    发件人: {sender.username if sender else '未知'} -> 收件人: {receiver.username if receiver else '未知'}")
                logger.info(f"    已读: {'是' if msg.is_read else '否'}")
            
            return True
    except Exception as e:
        logger.error(f"检查站内信时出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def create_test_message():
    """创建测试消息"""
    try:
        # 导入必要的模块
        from src import create_app
        from src.models import db, User, Role, Message
        
        # 创建应用上下文
        app = create_app()
        with app.app_context():
            logger.info("=== 创建测试消息 ===")
            
            # 1. 获取管理员和学生
            admin_role = db.session.execute(db.select(Role).filter_by(name='Admin')).scalar_one_or_none()
            student_role = db.session.execute(db.select(Role).filter_by(name='Student')).scalar_one_or_none()
            
            if not admin_role or not student_role:
                logger.error("角色不存在!")
                return False
            
            admin = db.session.execute(db.select(User).filter_by(role_id=admin_role.id)).scalar_one_or_none()
            student = db.session.execute(db.select(User).filter_by(role_id=student_role.id)).scalar_one_or_none()
            
            if not admin:
                logger.error("未找到管理员用户!")
                return False
            
            if not student:
                logger.error("未找到学生用户!")
                return False
            
            logger.info(f"将从管理员 {admin.username} (ID: {admin.id}) 发送消息给学生 {student.username} (ID: {student.id})")
            
            # 2. 创建测试消息
            now = datetime.now()
            message = Message(
                sender_id=admin.id,
                receiver_id=student.id,
                subject=f"测试消息 - {now.strftime('%Y-%m-%d %H:%M:%S')}",
                content=f"这是一条测试消息，用于验证站内信系统是否正常工作。\n\n发送时间: {now.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            db.session.add(message)
            db.session.commit()
            
            logger.info(f"测试消息创建成功! ID: {message.id}")
            return True
    except Exception as e:
        logger.error(f"创建测试消息时出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def fix_message_relations():
    """修复消息关联关系"""
    try:
        # 导入必要的模块
        from src import create_app
        from src.models import db, User, Message
        
        # 创建应用上下文
        app = create_app()
        with app.app_context():
            logger.info("=== 修复消息关联关系 ===")
            
            # 获取所有消息
            messages = db.session.execute(db.select(Message)).scalars().all()
            logger.info(f"发现 {len(messages)} 条消息")
            
            fixed_count = 0
            for msg in messages:
                # 检查发送者和接收者是否存在
                sender = db.session.get(User, msg.sender_id)
                receiver = db.session.get(User, msg.receiver_id)
                
                if not sender or not receiver:
                    logger.warning(f"消息 ID {msg.id} 的发送者或接收者不存在，标记为删除")
                    db.session.delete(msg)
                    fixed_count += 1
                    continue
            
            if fixed_count > 0:
                db.session.commit()
                logger.info(f"已修复 {fixed_count} 条问题消息")
            else:
                logger.info("没有发现需要修复的消息")
            
            return True
    except Exception as e:
        logger.error(f"修复消息关联关系时出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """主函数"""
    logger.info("==== 站内信系统调试工具 ====")
    
    # 1. 检查站内信状态
    logger.info("\n步骤1: 检查站内信状态")
    if not check_messages():
        logger.error("检查站内信状态失败")
    
    # 2. 修复消息关联关系
    logger.info("\n步骤2: 修复消息关联关系")
    if not fix_message_relations():
        logger.error("修复消息关联关系失败")
    
    # 3. 创建测试消息
    logger.info("\n步骤3: 创建测试消息")
    if not create_test_message():
        logger.error("创建测试消息失败")
    
    # 4. 再次检查状态
    logger.info("\n步骤4: 再次检查站内信状态")
    if not check_messages():
        logger.error("检查站内信状态失败")
    
    logger.info("\n==== 调试完成 ====")
    logger.info("如果测试消息已成功创建，请尝试登录学生账号查看是否能正常收到消息")

if __name__ == "__main__":
    main() 