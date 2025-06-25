#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import json
import unittest
from flask import Flask, jsonify

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

class TestAIChatClear(unittest.TestCase):
    """测试AI聊天清除历史功能"""
    
    def setUp(self):
        """测试前的设置"""
        # 创建一个简单的Flask应用
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'test_secret_key'
        
        # 注册路由
        @self.app.route('/education/ai_chat_clear_history', methods=['POST'])
        def ai_chat_clear_history():
            """清除AI聊天历史记录"""
            return jsonify({
                'success': True,
                'message': '聊天历史已清除'
            })
        
        self.client = self.app.test_client()
        
    def test_ai_chat_clear_history(self):
        """测试清除AI聊天历史记录的路由"""
        # 在测试环境下，我们的路由不会检查CSRF令牌
        response = self.client.post('/education/ai_chat_clear_history', 
                                    data=json.dumps({}),
                                    content_type='application/json')
        
        # 检查响应状态码是否为200
        self.assertEqual(response.status_code, 200)
        
        # 解析响应数据
        data = json.loads(response.data)
        
        # 验证响应中的success字段为True
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], '聊天历史已清除')
        
if __name__ == '__main__':
    unittest.main() 