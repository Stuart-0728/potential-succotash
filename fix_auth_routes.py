#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复登录路由问题脚本
"""

import os
import sys
import logging
import shutil
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def backup_files():
    """备份关键文件"""
    backup_dir = os.path.join('src', 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    files_to_backup = [
        'src/routes/auth.py'
    ]
    
    for file_path in files_to_backup:
        if os.path.exists(file_path):
            backup_path = os.path.join(backup_dir, f"{os.path.basename(file_path)}_{timestamp}")
            shutil.copy2(file_path, backup_path)
            logger.info(f"已备份 {file_path} 到 {backup_path}")
        else:
            logger.warning(f"文件 {file_path} 不存在，跳过备份")
    
    return True

def fix_auth_routes():
    """修复登录路由"""
    file_path = 'src/routes/auth.py'
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找login函数
        if '@auth_bp.route(\'/login\', methods=[\'GET\', \'POST\'])' in content:
            logger.info("找到login路由，开始修复...")
            
            # 修改login函数，增加错误处理和日志记录
            login_function = """@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    \"\"\"用户登录\"\"\"
    form = LoginForm()
    
    # 如果是GET请求，直接显示登录表单
    if request.method == 'GET':
        return render_template('auth/login.html', form=form)
    
    # 如果是POST请求，处理表单提交
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        
        logger.info(f"尝试登录: 用户名={username}")
        
        try:
            # 查询用户
            user = db.session.execute(db.select(User).filter_by(username=username)).scalar_one_or_none()
            
            if user and user.check_password(password):
                # 登录成功
                login_user(user)
                
                # 更新最后登录时间
                user.last_login = datetime.now()
                db.session.commit()
                
                logger.info(f"用户 {username} 登录成功")
                
                # 记录系统日志
                log = SystemLog(
                    user_id=user.id,
                    action='登录',
                    details=f'用户 {username} 登录成功',
                    ip_address=request.remote_addr
                )
                db.session.add(log)
                db.session.commit()
                
                # 获取next参数，如果有的话重定向到该页面
                next_page = request.args.get('next')
                if not next_page or url_parse(next_page).netloc != '':
                    if user.is_admin:
                        next_page = url_for('admin.dashboard')
                    else:
                        next_page = url_for('student.dashboard')
                
                flash('登录成功！', 'success')
                return redirect(next_page)
            else:
                # 登录失败
                logger.warning(f"用户 {username} 登录失败: 用户名或密码错误")
                flash('用户名或密码错误，请重试。', 'danger')
                return render_template('auth/login.html', form=form)
                
        except Exception as e:
            # 捕获所有异常，确保即使数据库查询失败也能正常显示错误信息
            logger.error(f"登录查询错误: {str(e)}")
            logger.error(f"登录过程发生错误: {str(e)}", exc_info=True)
            flash('登录过程中发生错误，请稍后再试。', 'danger')
            return render_template('auth/login.html', form=form)
    
    # 表单验证失败
    return render_template('auth/login.html', form=form)"""
            
            # 替换login函数
            import re
            pattern = r'@auth_bp\.route\(\'\/login\'\, methods=\[\'GET\'\, \'POST\'\]\).*?def login\(\):.*?(?=@auth_bp\.route|$)'
            new_content = re.sub(pattern, login_function, content, flags=re.DOTALL)
            
            # 写回文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            logger.info(f"已修复 {file_path} 中的login函数")
        else:
            logger.warning(f"在 {file_path} 中未找到login路由，跳过修复")
        
        return True
    except Exception as e:
        logger.error(f"修复 {file_path} 时出错: {e}")
        return False

def main():
    """主函数"""
    logger.info("开始修复登录路由问题...")
    
    # 备份文件
    if not backup_files():
        logger.error("备份文件失败，终止修复")
        return False
    
    # 修复文件
    if not fix_auth_routes():
        logger.error("修复登录路由失败")
        return False
    
    logger.info("登录路由修复完成！")
    logger.info("请重启应用以应用更改")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 