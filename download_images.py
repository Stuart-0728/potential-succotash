import urllib.request
import os
import ssl

# 禁用SSL证书验证
ssl._create_default_https_context = ssl._create_unverified_context

# 确保目录存在
os.makedirs('src/static/img', exist_ok=True)

# 定义不同主题的图片URL
urls = [
    'https://picsum.photos/1200/500?random=1&blur=2',  # 模糊艺术风格
    'https://picsum.photos/1200/500?random=2&grayscale',  # 黑白风格
    'https://picsum.photos/1200/500?random=3&theme=education',  # 教育主题
    'https://picsum.photos/1200/500?random=4&theme=nature',  # 自然风景
    'https://picsum.photos/1200/500?random=5&theme=campus',  # 校园风格
    'https://picsum.photos/1200/500?random=6&theme=technology'  # 科技风格
]

for i, url in enumerate(urls, 1):
    try:
        print(f"正在下载 banner{i}.jpg...")
        urllib.request.urlretrieve(url, f'src/static/img/banner{i}.jpg')
        print(f"下载完成: banner{i}.jpg")
    except Exception as e:
        print(f"下载失败: {e}")

print("所有图片下载完成！") 