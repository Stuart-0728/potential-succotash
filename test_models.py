#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试模型导入
"""

try:
    from src.models import db, AIChatHistory, AIChatSession, AIUserPreferences
    print("成功导入AI聊天模型类")
except ImportError as e:
    print(f"导入失败: {e}") 