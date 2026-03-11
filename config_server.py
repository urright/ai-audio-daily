#!/usr/bin/env python3
"""
简单的配置文件 Web 编辑器
访问 http://localhost:8080 查看和编辑 profiles.json
提交后自动写入文件，无需重启。
"""

import http.server
import socketserver
import json
import os
from pathlib import Path

PORT = 8080
PROFILES_FILE = 'profiles.json'

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path != '/':
            return super().do_GET()
        # 主页面：显示表单
        try:
            with open(PROFILES_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            content = '[]'

        html = f'''<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>OpenClaw 日报配置管理</title>
  <style>
    body {{ font-family: sans-serif; margin: 2rem; }}
    textarea {{ width: 100%; height: 80vh; font-family: monospace; font-size: 14px; }}
    input[type="submit"] {{ padding: 0.8rem 1.5rem; font-size: 16px; }}
    .note {{ color: #666; font-size: 0.9rem; margin-top: 1rem; }}
  </style>
</head>
<body>
  <h1>OpenClaw 日报 · 配置文件</h1>
  <form method="POST" action="/">
    <textarea name="profiles">{json.dumps(json.loads(content), indent=2, ensure_ascii=False)}</textarea>
    <br><br>
    <input type="submit" value="保存并验证">
  </form>
  <div class="note">
    <p>提示：请保持 JSON 格式正确。每个 profile 字段说明：</p>
    <ul>
      <li><code>name</code>: 唯一标识（英文，无空格）</li>
      <li><code>description</code>: 描述（中文）</li>
      <li><code>config_dir</code>: RSS/YouTube 配置目录（如 "config"、"config_openclaw"）</li>
      <li><code>output_dir</code>: 输出目录（如 "docs/it"、"docs/oc"）</li>
      <li><code>audio_subdir</code>: 音频子目录（如 "audio"）</li>
      <li><code>url_path</code>: GitHub Pages 路径（相对于 docs/ 之后的部分，如 "it"、"oc"）</li>
      <li><code>telegram_bot_token</code>: Telegram Bot Token（可用 ${VAR} 从环境变量展开）</li>
      <li><code>telegram_chat_id</code>: Telegram 群组/用户 ID（可用 ${VAR}）</li>
      <li><code>schedule</code>: Cron 表达式（如 "30 7 * * *"）</li>
      <li><code>enabled</code>: true/false</li>
    </ul>
    <p>保存后，新配置将在下次 cron 运行时生效。如需立即运行，可使用：<br><code>python3 main.py --profile &lt;name&gt;</code></p>
  </div>
</body>
</html>'''
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def do_POST(self):
        content_len = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_len).decode('utf-8')
        # 解析 profiles 参数
        try:
            # 解析 "profiles=..." URL 编码数据
            from urllib.parse import parse_qs
            parsed = parse_qs(post_data)
            profiles_raw = parsed.get('profiles', [''])[0]
            profiles_data = json.loads(profiles_raw)
            # 验证 JSON 是否为列表
            if not isinstance(profiles_data, list):
                raise ValueError("profiles 必须是数组")
            # 写入文件
            with open(PROFILES_FILE, 'w', encoding='utf-8') as f:
                json.dump(profiles_data, f, indent=2, ensure_ascii=False)
            resp = f'''<!doctype html>
<html><body>
<h1>✅ 配置已保存</h1>
<p>共保存 {len(profiles_data)} 个 profile。</p>
<p>回到 <a href="/">配置页面</a></p>
</body></html>'''
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(resp.encode('utf-8'))
        except Exception as e:
            error_msg = f'❌ 保存失败: {str(e)}'
            self.send_response(400)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(f'<html><body><h1>{error_msg}</h1><a href="/">返回</a></body></html>'.encode('utf-8'))

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)) or '.')
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"🔧 配置服务器启动：http://localhost:{PORT}")
        print("按 Ctrl+C 停止")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 服务器已停止")
