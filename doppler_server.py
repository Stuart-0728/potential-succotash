import http.server
import socketserver
import os
import uuid
from urllib.parse import urlparse

# 配置端口
PORT = 8080

# 创建一个自定义的请求处理器
class DopplerHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # 解析请求路径
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # 如果请求的是根路径，重定向到doppler-effect.html
        if path == '/':
            self.send_response(302)
            self.send_header('Location', '/doppler-effect.html')
            self.end_headers()
            return
            
        # 为所有请求添加安全头
        self.send_response(200)
        self.send_header('Content-Type', self.guess_type(path))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' https://cdn.tailwindcss.com https://cdn.jsdelivr.net 'unsafe-inline'; style-src 'self' https://fonts.googleapis.com 'unsafe-inline'; font-src 'self' https://fonts.gstatic.com; connect-src 'self' https://generativelanguage.googleapis.com;")
        self.send_header('X-XSS-Protection', '1; mode=block')
        self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')
        self.send_header('Permissions-Policy', 'microphone=(), camera=()')
        
        # 为HTML文件添加CSRF令牌
        if path.endswith('.html'):
            # 生成一个随机的CSRF令牌
            csrf_token = str(uuid.uuid4())
            self.send_header('Set-Cookie', f'csrf_token={csrf_token}; Path=/; SameSite=Strict; Secure')
            
        self.end_headers()
        
        # 调用父类方法处理文件内容
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        # 对于POST请求，我们需要模拟API响应
        if self.path == '/api/gemini':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            # 这里我们只是返回一个简单的成功响应
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            response = '{"success":true,"content":"这是一个模拟的API响应。在实际部署中，这将连接到真正的AI服务。"}'
            self.wfile.write(response.encode('utf-8'))
            return
        else:
            # 其他POST请求返回404
            self.send_response(404)
            self.end_headers()

# 创建服务器
Handler = DopplerHTTPRequestHandler
httpd = socketserver.TCPServer(("", PORT), Handler)

print(f"启动服务器在端口 {PORT}...")
print(f"访问 http://localhost:{PORT}/doppler-effect.html 查看演示")

# 启动服务器
try:
    httpd.serve_forever()
except KeyboardInterrupt:
    print("\n服务器已停止")
    httpd.server_close() 