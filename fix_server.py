#!/usr/bin/env python3
"""
修复时间显示和签到问题的脚本
"""

import os
import subprocess
import sys
import time

# 修复的问题总结
FIXES_SUMMARY = """
# 修复总结

## 已修复的问题:

1. 时区和时间显示问题:
   - 修复了activity.start_time显示为UTC时间而非北京时间的问题
   - 确保所有时间正确转换为北京时间显示
   - 增强了display_datetime函数的日志输出，帮助调试

2. 报名人数和签到人数计算问题:
   - 修复了签到后报名人数显示为0的问题
   - 确保签到人数正确统计
   - 修改了Registration查询逻辑，同时考虑'registered'和'attended'两种状态

3. 签到页面无法访问问题:
   - 修复了checkin_modal路由，确保正确查询签到记录
   - 确保display_datetime函数被传递给所有相关模板

4. 日志路径错误:
   - 修复了日志文件路径问题，确保logs目录存在

## 修复的文件:

1. src/main.py - 修复日志文件路径
2. src/forms.py - 修改LocalizedDateTimeField.populate_obj方法，避免时区转换错误
3. src/utils/time_helpers.py - 改进display_datetime函数，确保正确显示北京时间
4. src/routes/admin.py - 修复签到页面和活动详情页面
5. src/routes/checkin.py - 修改签到状态更新逻辑
6. src/routes/student.py - 修复学生活动详情页面，更新报名和签到人数计算

## 重要修改:

1. 确保签到时用户状态改为'attended'
2. 确保报名人数统计包括'registered'和'attended'两种状态
3. 统一使用display_datetime函数显示时间
4. 优化时区处理逻辑，确保时间一致性
"""

def print_colored(text, color):
    """打印彩色文本"""
    colors = {
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'purple': '\033[95m',
        'cyan': '\033[96m',
        'white': '\033[97m',
        'end': '\033[0m'
    }
    print(f"{colors.get(color, '')}{text}{colors['end']}")

def ensure_logs_directory():
    """确保logs目录存在"""
    if not os.path.exists('src/logs'):
        os.makedirs('src/logs')
        print_colored("已创建日志目录: src/logs", "green")
    else:
        print_colored("日志目录已存在", "blue")

def restart_server(port=8080):
    """重启Flask服务器"""
    print_colored(f"正在启动服务器，端口: {port}...", "yellow")
    
    # 切换到src目录
    os.chdir('src')
    
    # 启动Flask应用
    try:
        subprocess.run([sys.executable, 'main.py', f'--port={port}'])
    except KeyboardInterrupt:
        print_colored("\n服务器已停止", "yellow")
    except Exception as e:
        print_colored(f"启动服务器时出错: {e}", "red")

def main():
    """主函数"""
    print_colored("=" * 60, "cyan")
    print_colored("CQNU社团管理系统修复工具", "cyan")
    print_colored("=" * 60, "cyan")
    
    print_colored(FIXES_SUMMARY, "white")
    print_colored("=" * 60, "cyan")
    
    # 确保logs目录存在
    ensure_logs_directory()
    
    # 询问是否重启服务器
    response = input("是否要重启服务器? (y/n): ").strip().lower()
    if response == 'y':
        port = input("请输入端口号 (默认: 8080): ").strip()
        port = int(port) if port.isdigit() else 8080
        restart_server(port)
    else:
        print_colored("退出程序，未重启服务器", "yellow")

if __name__ == "__main__":
    main() 