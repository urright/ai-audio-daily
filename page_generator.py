import json
from datetime import datetime
from pathlib import Path
from jinja2 import Template

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 办公自动化日报 - {{ date }}</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
        .header { text-align: center; margin-bottom: 30px; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 10px; }
        .category { background: white; margin: 20px 0; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .category h2 { color: #667eea; border-bottom: 2px solid #667eea; padding-bottom: 10px; }
        .entry { margin: 15px 0; padding: 15px; border-left: 3px solid #667eea; background: #f9f9f9; }
        .entry h3 { margin: 0 0 10px 0; color: #333; font-size: 1.1em; }
        .entry p { margin: 5px 0; color: #666; line-height: 1.6; }
        .entry a { color: #667eea; text-decoration: none; }
        .entry a:hover { text-decoration: underline; }
        .audio-link { display: inline-block; margin: 5px 5px 5px 0; padding: 5px 10px; background: #667eea; color: white; border-radius: 4px; text-decoration: none; font-size: 0.9em; }
        .footer { text-align: center; margin-top: 30px; color: #999; font-size: 0.9em; }
        .back-to-top { position: fixed; bottom: 20px; right: 20px; background: #667eea; color: white; padding: 10px 15px; border-radius: 50px; text-decoration: none; box-shadow: 0 2px 8px rgba(0,0,0,0.2); }
    </style>
</head>
<body>
    <div class="header">
        <h1>🎧 AI 办公自动化日报</h1>
        <p>{{ date }} · 共收集 {{ total_items }} 条内容</p>
        <p><a href="#audio-summary" style="color: white;">▶️ 收听语音摘要</a></p>
    </div>

    {% for category, entries in categorized.items() %}
    <div class="category" id="category-{{ category }}">
        <h2>{{ category_name(category) }} ({{ entries|length }})</h2>
        {% for entry in entries %}
        <div class="entry">
            <h3>{{ loop.index }}. {{ entry.title }}</h3>
            <p>{{ entry.short_summary }}</p>
            <p>
                <strong>来源：</strong>{{ entry.source }} | 
                <strong>时间：</strong>{{ entry.published[:10] }}
            </p>
            <p>
                {% if entry.source == 'youtube' %}
                <a href="{{ entry.url }}" target="_blank" class="audio-link">🎬 观看原视频</a>
                {% else %}
                <a href="{{ entry.link }}" target="_blank" class="audio-link">📖 阅读原文</a>
                {% endif %}
                <a href="#audio-summary" class="audio-link">🔊 收听片段</a>
            </p>
        </div>
        {% endfor %}
    </div>
    {% endfor %}

    <div class="category" id="audio-summary">
        <h2>🎵 语音摘要</h2>
        <audio controls style="width: 100%; max-width: 600px;">
            <source src="{{ audio_path }}" type="audio/mpeg">
            您的浏览器不支持audio标签。
        </audio>
        <p><small>点击播放今日语音简报（约2-3分钟）</small></p>
    </div>

    <a href="#" class="back-to-top">↑ 回到顶部</a>

    <div class="footer">
        <p>由 AI Agent 自动生成 · 每日更新</p>
        <p>Powered by OpenClaw + Agent Reach</p>
    </div>
</body>
</html>
"""

class PageGenerator:
    def __init__(self, template_str=HTML_TEMPLATE):
        self.template = Template(template_str)

    def category_name(self, cat):
        names = {
            'release': '版本发布',
            'feature': '新功能',
            'tutorial': '使用教程',
            'discussion': '社区讨论',
            'skill': '技能市场',
            'bugfix': '问题修复',
            'announcement': '官方公告',
            'general': '其他动态'
        }
        return names.get(cat, cat)

    def generate(self, categorized_data, audio_filename, output_path="public/index.html"):
        """生成HTML页面"""
        date_str = datetime.now().strftime("%Y年%m月%d日")
        total = sum(len(entries) for entries in categorized_data.values())

        html = self.template.render(
            date=date_str,
            categorized=categorized_data,
            category_name=self.category_name,
            total_items=total,
            audio_path=f"audio/{audio_filename}"
        )

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"✅ 页面已生成: {output_path}")
        return output_path

if __name__ == "__main__":
    # 测试
    with open("data/processed.json", 'r', encoding='utf-8') as f:
        categorized = json.load(f)

    generator = PageGenerator()
    html = generator.generate(categorized, "daily_summary.mp3", "public/test.html")
    print(f"Generated: {html}")
