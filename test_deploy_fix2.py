#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
部署脚本 - 将最新修复后的代码推送到render.com
"""

import os
import sys
import subprocess
import logging
import time
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_command(command, cwd=None):
    """运行命令并返回结果"""
    logger.info(f"执行命令: {command}")
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True,
            cwd=cwd
        )
        logger.info(f"命令执行成功: {result.stdout}")
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"命令执行失败: {e.stderr}")
        return False, e.stderr

def deploy_to_render():
    """部署到Render.com"""
    try:
        # 获取当前目录
        current_dir = os.getcwd()
        logger.info(f"当前目录: {current_dir}")
        
        # 检查是否是git仓库
        success, output = run_command("git status", cwd=current_dir)
        if not success:
            logger.error("当前目录不是git仓库")
            return False
        
        # 添加修改的文件
        logger.info("添加修改的文件...")
        run_command("git add src/routes/admin.py", cwd=current_dir)
        
        # 提交修改
        commit_message = f"进一步修复活动编辑中的标签处理问题 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        logger.info(f"提交修改: {commit_message}")
        run_command(f'git commit -m "{commit_message}"', cwd=current_dir)
        
        # 推送到远程仓库
        logger.info("推送到远程仓库...")
        success, output = run_command("git push", cwd=current_dir)
        if not success:
            logger.error("推送失败")
            return False
        
        logger.info("代码已成功推送到远程仓库")
        logger.info("Render.com将自动部署最新代码")
        
        # 等待部署完成
        logger.info("等待部署完成...")
        time.sleep(10)
        logger.info("部署应该已经开始，可以在Render.com控制台查看部署状态")
        
        return True
        
    except Exception as e:
        logger.error(f"部署过程中出错: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    logger.info("开始部署最新修复后的代码...")
    success = deploy_to_render()
    if success:
        logger.info("部署成功完成")
        sys.exit(0)
    else:
        logger.error("部署失败")
        sys.exit(1) 