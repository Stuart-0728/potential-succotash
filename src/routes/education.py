import sys
import os
import json
import uuid
import requests
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
            "description": "重庆师范大学官方网站，提供学校新闻、通知和资源"
        },
        {
            "name": "中国教育资源网",
            "url": "http://www.cersp.com/",
            "icon": "fa-book",
            "description": "综合性教育资源门户，提供各学科教学资源和教育新闻"
        },
        {
            "name": "学科网",
            "url": "https://www.zxxk.com/",
            "icon": "fa-pencil-alt",
            "description": "提供中小学各学科教案、试卷、课件等教学资源"
        },
        {
            "name": "全国教师管理信息系统",
            "url": "https://www.jszg.edu.cn/",
            "icon": "fa-id-card",
            "description": "教师资格证查询和管理的官方平台"
        },
        {
            "name": "中国知网",
            "url": "https://www.cnki.net/",
            "icon": "fa-file-alt",
            "description": "中国知识基础设施工程，提供学术论文和期刊资源"
        },
        {
            "name": "物理实验在线",
            "url": "http://en.wuli.ac.cn/",
            "icon": "fa-atom",
            "description": "提供物理实验的在线模拟和教学资源"
        },
        {
            "name": "中国化学教育网",
            "url": "http://www.chemhtml.com/",
            "icon": "fa-flask",
            "description": "化学教育资源平台，提供教学课件和实验指导"
        },
        {
            "name": "中国数字教育资源公共服务平台",
            "url": "http://www.eduyun.cn/",
            "icon": "fa-cloud",
            "description": "教育部主管的数字教育资源服务平台"
        },
        {
            "name": "PhET互动科学模拟",
            "url": "https://phet.colorado.edu/zh_CN/",
            "icon": "fa-microscope",
            "description": "科罗拉多大学提供的互动科学模拟实验平台"
        }
    ]
    
    # 本地教育资源列表
    local_resources = [
        {
            "name": "自由落体运动探究",
            "url": url_for('education.free_fall'),
            "icon": "fa-arrow-down",
            "description": "通过交互式实验探究自由落体运动规律，理解伽利略的贡献"
        }
    ]
    
    return render_template('education/resources.html', 
                          online_resources=online_resources,
                          local_resources=local_resources)

@education_bp.route('/resource/free-fall')
def free_fall():
    """自由落体运动探究页面"""
    return render_template('education/free_fall.html')

@education_bp.route('/api/gemini', methods=['POST'])
@login_required
def gemini_api():
    """处理Gemini API请求"""
    data = request.json
    if not data or 'prompt' not in data:
        return jsonify({
            'success': False,
            'error': '请求格式错误，缺少prompt字段'
        }), 400
    
    prompt = data['prompt']
    
    # 记录API调用
    log_action(
        user_id=current_user.id,
        action="教育资源API调用",
        details=f"调用教育资源API，提示词长度：{len(prompt)}"
    )
    
    # 获取API密钥
    api_key = os.environ.get("ARK_API_KEY")
    if not api_key:
        # 尝试从应用配置获取API密钥
        api_key = current_app.config.get('VOLCANO_API_KEY')
        if not api_key:
            current_app.logger.error("未找到API密钥，既没有ARK_API_KEY环境变量，也没有VOLCANO_API_KEY配置")
            return jsonify({
                'success': False,
                'content': '抱歉，AI服务暂时不可用：未配置API密钥',
                'error': 'AI 服务配置错误：API 密钥未设置'
            }), 200  # 返回200而不是500，这样前端可以显示错误消息
    
    # API端点
    url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    
    # 如果API密钥是火山引擎API密钥格式，则使用火山引擎API端点
    if api_key and (api_key.startswith("ccde") or 'VOLCANO_API_KEY' in os.environ):
        url = "https://render-api.volcengine.com/api/v1/chat/completions"
        current_app.logger.info("使用火山引擎API端点")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # 如果是火山引擎API，需要添加请求ID
    if url.startswith("https://ark.cn-beijing.volces.com"):
        headers["X-Request-Id"] = str(uuid.uuid4())
    
    payload = {
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "model": "glm-4",
        "temperature": 0.7,
        "top_p": 0.8,
        "max_tokens": 1000
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        # 检查响应
        if response.status_code == 200:
            result = response.json()
            
            # 根据返回结果结构提取内容
            if 'choices' in result and len(result['choices']) > 0:
                if 'message' in result['choices'][0]:
                    content = result['choices'][0]['message'].get('content', '')
                else:
                    content = result['choices'][0].get('text', '')
                
                return jsonify({
                    'success': True,
                    'content': content
                })
            else:
                error_msg = f"API响应格式异常: {result}"
                current_app.logger.error(error_msg)
                return jsonify({
                    'success': False,
                    'content': '抱歉，AI服务响应格式异常，请稍后再试',
                    'error': error_msg
                }), 200
        else:
            error_msg = f"API请求失败，状态码: {response.status_code}，响应内容: {response.text}"
            current_app.logger.error(error_msg)
            return jsonify({
                'success': False,
                'content': '抱歉，AI服务暂时不可用，请稍后再试',
                'error': error_msg
            }), 200
    
    except Exception as e:
        error_msg = f"API请求异常: {str(e)}"
        current_app.logger.error(error_msg)
        return jsonify({
            'success': False,
            'content': '抱歉，连接AI服务时遇到问题，请稍后再试',
            'error': error_msg
        }), 200 