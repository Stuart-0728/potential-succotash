import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import current_user, login_required
from src.models import db, User, Role
from src.routes.utils import log_action
from src.utils.time_helpers import get_localized_now

# 创建蓝图
education_bp = Blueprint('education', __name__)

@education_bp.route('/resources')
def resources():
    """显示教育资源页面"""
    # 网络教育资源列表
    online_resources = [
        {
            "name": "国家中小学智慧教育平台",
            "url": "https://www.zxx.edu.cn/",
            "icon": "fa-school",
            "description": "国家级中小学教育平台，提供丰富的教学资源和教育服务"
        },
        {
            "name": "重庆师范大学官网",
            "url": "https://www.cqnu.edu.cn/",
            "icon": "fa-university",
            "description": "重庆师范大学官方网站，提供学校信息和教育资源"
        },
        {
            "name": "中国教师教育网",
            "url": "http://www.teacher.com.cn/",
            "icon": "fa-chalkboard-teacher",
            "description": "面向教师的专业发展平台，提供教学资源和教育研究"
        },
        {
            "name": "人民教育出版社",
            "url": "https://www.pep.com.cn/",
            "icon": "fa-book",
            "description": "提供教材资源和教学指导，支持教师备课和教学"
        },
        {
            "name": "学科网",
            "url": "https://www.zxxk.com/",
            "icon": "fa-atom",
            "description": "中小学教学资源平台，提供各学科教案、试题和课件"
        },
        {
            "name": "PhET互动式模拟实验",
            "url": "https://phet.colorado.edu/zh_CN/",
            "icon": "fa-flask",
            "description": "科学和数学互动模拟实验，支持探究式学习"
        },
        {
            "name": "可汗学院",
            "url": "https://zh.khanacademy.org/",
            "icon": "fa-video",
            "description": "免费教育视频和练习，覆盖多个学科领域"
        },
        {
            "name": "中国大学MOOC",
            "url": "https://www.icourse163.org/",
            "icon": "fa-graduation-cap",
            "description": "国内领先的大规模开放在线课程平台，提供高质量大学课程"
        },
        {
            "name": "教师教育网",
            "url": "http://www.jsjyw.com/",
            "icon": "fa-user-graduate",
            "description": "教师专业发展资源网站，提供教学方法和教育理论"
        },
        {
            "name": "智慧学习空间",
            "url": "http://www.ssedu.net/",
            "icon": "fa-brain",
            "description": "智能化教育资源平台，支持个性化学习和教学"
        }
    ]
    
    # 本地教育资源列表
    local_resources = [
        {
            "name": "自由落体运动探究",
            "url": "/education/resource/free-fall",
            "icon": "fa-arrow-down",
            "description": "交互式探究自由落体运动的物理概念和应用"
        }
    ]
    
    return render_template('education/resources.html', 
                          online_resources=online_resources,
                          local_resources=local_resources,
                          now=get_localized_now())

@education_bp.route('/resource/free-fall')
def free_fall():
    """显示自由落体运动探究页面"""
    # 记录访问日志
    if current_user.is_authenticated:
        log_action('view_resource', f'用户 {current_user.username} 访问了自由落体运动探究资源')
    
    return render_template('education/free_fall.html', now=get_localized_now())

@education_bp.route('/api/gemini', methods=['POST'])
@login_required
def gemini_api():
    """处理Gemini API请求"""
    try:
        data = request.get_json()
        if not data or 'prompt' not in data:
            return jsonify({'error': '缺少必要参数'}), 400
        
        prompt = data['prompt']
        
        # 使用火山API替代原来的Gemini API
        import requests
        
        # 火山API配置
        api_key = current_app.config.get('VOLCANO_API_KEY', '')
        api_url = "https://render-api.volcengine.com/api/v1/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        payload = {
            "model": "volcengine-gpt-4",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 800
        }
        
        response = requests.post(api_url, json=payload, headers=headers)
        
        if response.status_code != 200:
            return jsonify({'error': f'API请求失败: {response.text}'}), 500
        
        result = response.json()
        
        # 提取回复内容
        if 'choices' in result and len(result['choices']) > 0:
            content = result['choices'][0]['message']['content']
            return jsonify({'content': content})
        else:
            return jsonify({'error': '无法获取有效的回答'}), 500
            
    except Exception as e:
        current_app.logger.error(f"Gemini API错误: {str(e)}")
        return jsonify({'error': f'处理请求时出错: {str(e)}'}), 500 