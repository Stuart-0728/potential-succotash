#!/usr/bin/env bash
# 安装系统级依赖，包括编译工具和开发库
apt-get update -y
apt-get install -y build-essential python3-dev libffi-dev

# 升级pip
pip install --upgrade pip

# 安装项目依赖
pip install -r requirements.txt 