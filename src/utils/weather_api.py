import requests
import logging
from datetime import datetime, timedelta
from flask import current_app
import json

logger = logging.getLogger(__name__)

class WeatherService:
    """天气服务类，用于获取重庆天气信息"""
    
    def __init__(self):
        # 使用免费的OpenWeatherMap API
        # 您需要在环境变量中设置OPENWEATHER_API_KEY
        self.api_key = current_app.config.get('OPENWEATHER_API_KEY', 'demo_key')
        self.base_url = "http://api.openweathermap.org/data/2.5"
        self.city_name = "Chongqing,CN"  # 重庆
        
    def get_current_weather(self):
        """获取重庆当前天气"""
        try:
            url = f"{self.base_url}/weather"
            params = {
                'q': self.city_name,
                'appid': self.api_key,
                'units': 'metric',  # 摄氏度
                'lang': 'zh_cn'     # 中文
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return self._format_weather_data(data)
            else:
                logger.error(f"天气API请求失败: {response.status_code}")
                return self._get_fallback_weather()
                
        except Exception as e:
            logger.error(f"获取天气数据失败: {e}")
            return self._get_fallback_weather()
    
    def get_weather_by_date(self, target_date):
        """获取指定日期的天气预报（最多支持5天）"""
        try:
            # 计算目标日期与今天的差异
            today = datetime.now().date()
            target_date_obj = target_date.date() if hasattr(target_date, 'date') else target_date
            days_diff = (target_date_obj - today).days
            
            # 如果是今天或过去的日期，返回当前天气
            if days_diff <= 0:
                return self.get_current_weather()
            
            # 如果超过5天，返回当前天气作为参考
            if days_diff > 5:
                weather_data = self.get_current_weather()
                weather_data['is_forecast'] = False
                weather_data['note'] = '活动日期较远，显示当前天气供参考'
                return weather_data
            
            # 获取5天预报
            url = f"{self.base_url}/forecast"
            params = {
                'q': self.city_name,
                'appid': self.api_key,
                'units': 'metric',
                'lang': 'zh_cn'
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                # 查找目标日期的天气
                for item in data['list']:
                    forecast_date = datetime.fromtimestamp(item['dt']).date()
                    if forecast_date == target_date_obj:
                        weather_data = self._format_weather_data(item, is_forecast=True)
                        weather_data['forecast_date'] = target_date_obj.strftime('%Y-%m-%d')
                        return weather_data
                
                # 如果没找到精确日期，返回最接近的预报
                closest_item = min(data['list'], 
                                 key=lambda x: abs((datetime.fromtimestamp(x['dt']).date() - target_date_obj).days))
                weather_data = self._format_weather_data(closest_item, is_forecast=True)
                weather_data['forecast_date'] = target_date_obj.strftime('%Y-%m-%d')
                weather_data['note'] = '显示最接近活动日期的天气预报'
                return weather_data
            else:
                logger.error(f"天气预报API请求失败: {response.status_code}")
                return self._get_fallback_weather()
                
        except Exception as e:
            logger.error(f"获取天气预报失败: {e}")
            return self._get_fallback_weather()
    
    def _format_weather_data(self, data, is_forecast=False):
        """格式化天气数据"""
        try:
            # 处理不同的数据结构（当前天气 vs 预报）
            if 'main' in data:
                main_data = data['main']
                weather_data = data['weather'][0]
            else:
                main_data = data
                weather_data = data.get('weather', [{}])[0]
            
            # 天气图标映射
            icon_map = {
                '01d': 'sunny',      # 晴天
                '01n': 'clear-night', # 晴夜
                '02d': 'partly-cloudy', # 少云
                '02n': 'partly-cloudy-night',
                '03d': 'cloudy',     # 多云
                '03n': 'cloudy',
                '04d': 'overcast',   # 阴天
                '04n': 'overcast',
                '09d': 'rainy',      # 小雨
                '09n': 'rainy',
                '10d': 'rainy',      # 中雨
                '10n': 'rainy',
                '11d': 'thunderstorm', # 雷雨
                '11n': 'thunderstorm',
                '13d': 'snowy',      # 雪
                '13n': 'snowy',
                '50d': 'foggy',      # 雾
                '50n': 'foggy'
            }
            
            icon_code = weather_data.get('icon', '01d')
            weather_type = icon_map.get(icon_code, 'sunny')
            
            return {
                'temperature': round(main_data.get('temp', 20)),
                'description': weather_data.get('description', '晴天'),
                'humidity': main_data.get('humidity', 60),
                'feels_like': round(main_data.get('feels_like', 20)),
                'weather_type': weather_type,
                'icon': icon_code,
                'is_forecast': is_forecast,
                'city': '重庆',
                'success': True
            }
        except Exception as e:
            logger.error(f"格式化天气数据失败: {e}")
            return self._get_fallback_weather()
    
    def _get_fallback_weather(self):
        """获取备用天气数据（当API失败时）"""
        return {
            'temperature': 22,
            'description': '多云',
            'humidity': 65,
            'feels_like': 24,
            'weather_type': 'cloudy',
            'icon': '03d',
            'is_forecast': False,
            'city': '重庆',
            'success': False,
            'note': '天气数据获取失败，显示默认数据'
        }

# 全局天气服务实例
weather_service = None

def get_weather_service():
    """获取天气服务实例"""
    global weather_service
    if weather_service is None:
        weather_service = WeatherService()
    return weather_service

def get_activity_weather(activity_start_time):
    """获取活动当天的天气信息"""
    service = get_weather_service()
    return service.get_weather_by_date(activity_start_time)
