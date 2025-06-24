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
    try:
        data = request.json
        if not data or 'prompt' not in data:
            return jsonify({
                'success': False,
                'error': '请求格式错误，缺少prompt字段'
            })
        
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
                    'content': '系统未配置API密钥，无法使用AI功能'
                })
        
        # 构建请求火山引擎的参数
        payload = {
            "model": {
                "name": "deepseek-chat"
            },
            "parameters": {
                "max_tokens": 1024,
                "temperature": 0.7,
                "top_p": 0.9,
                "do_sample": True
            },
            "messages": [
                {
                    "role": "system",
                    "content": "你是一名教育专家，精通物理学、数学等自然科学领域的知识。你正在为重庆师范大学师能素质协会的学生提供教育资源和答疑解惑。你的回答应该简洁、准确、有教育意义。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        # 发送请求
        url = "https://maas.volces.com/v1/services/aigc-api/requests/generate"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        # 记录请求开始
        current_app.logger.info(f"正在向火山引擎API发送请求，提示词长度：{len(prompt)}")
        
        response = requests.post(url, json=payload, headers=headers)
        
        # 记录响应状态
        current_app.logger.info(f"火山引擎API响应状态码：{response.status_code}")
        
        if response.status_code != 200:
            current_app.logger.error(f"火山引擎API调用失败，状态码：{response.status_code}，响应：{response.text}")
            return jsonify({
                'success': False,
                'content': f"AI服务暂时不可用，请稍后再试。错误码：{response.status_code}"
            })
        
        response_data = response.json()
        
        if 'data' in response_data and 'messages' in response_data['data'] and len(response_data['data']['messages']) > 0:
            ai_response = response_data['data']['messages'][0]['content']
            
            # 记录成功响应
            current_app.logger.info(f"成功获取AI响应，长度：{len(ai_response)}")
            
            return jsonify({
                'success': True,
                'content': ai_response
            })
        else:
            current_app.logger.error(f"API响应格式异常：{response_data}")
            return jsonify({
                'success': False,
                'content': "AI响应格式错误，请稍后再试"
            })
    
    except Exception as e:
        current_app.logger.error(f"Gemini API处理异常：{str(e)}")
        return jsonify({
            'success': False,
            'content': f"处理请求时发生错误：{str(e)}"
        }) 