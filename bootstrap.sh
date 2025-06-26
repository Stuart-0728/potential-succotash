#!/bin/bash

# 显示开始信息
echo "启动引导脚本..."

# 升级pip
pip3 install --upgrade pip

# 为确保依赖可用，先安装兼容Python 3.6的依赖
echo "正在安装依赖..."
pip3 install -r requirements.txt || {
    echo "依赖安装失败，重试..."
    pip3 install --no-cache-dir -r requirements.txt
}

# 检查是否成功安装
if [ $? -ne 0 ]; then
    echo "依赖安装失败，尝试使用兼容模式..."
    pip3 install -r requirements.txt --use-deprecated=legacy-resolver
fi

# 显示完成信息
echo "依赖安装完成，启动应用..."

# 使用Python 3运行app.py
/var/lang/python3/bin/python3 app.py 