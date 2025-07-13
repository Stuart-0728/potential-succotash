#!/usr/bin/env bash
# 安装系统级依赖，包括编译工具和开发库
echo "跳过系统级依赖安装，因为Render环境限制"

# 升级pip
pip install --upgrade pip setuptools wheel

# 使用wheels而不是从源码构建
export PIP_PREFER_BINARY=1

# 获取正确的requirements.txt路径
if [ -f "render_deploy/requirements.txt" ]; then
    REQUIREMENTS_PATH="render_deploy/requirements.txt"
elif [ -f "requirements.txt" ]; then
    REQUIREMENTS_PATH="requirements.txt"
else
    echo "无法找到requirements.txt文件"
    exit 1
fi

# 使用修改后的requirements.txt安装依赖
pip install -r $REQUIREMENTS_PATH 