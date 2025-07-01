#!/usr/bin/env bash
# 安装系统级依赖，包括编译工具和开发库
apt-get update -y
apt-get install -y build-essential python3-dev libffi-dev libopenblas-dev liblapack-dev

# 升级pip
pip install --upgrade pip

# 首先安装numpy和pandas的预编译二进制包
pip install --only-binary=:all: numpy==1.19.5
pip install --only-binary=:all: pandas==1.1.5

# 安装其余项目依赖
grep -v "numpy\|pandas" requirements.txt > other_requirements.txt
pip install -r other_requirements.txt 