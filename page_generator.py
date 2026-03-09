import json
from datetime import datetime
from pathlib import Path
from jinja2 import Template

# 详情页模板
DETAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenClaw 日报 - {{ date }}</title>
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
        <h1>🎧 OpenClaw 生态日报</h1>
        <p>{{ date }} · 共收集 {{ total_items }} 条动态</p>
        <p><a href="#audio-summary" style="color: white;">▶️ 收听语音摘要</a></p>
        <p style="margin-top: 10px;"><a href="../../index.html" style="color: white;">📋 返回主页</a></p>
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
            </p>
        </div>
        {% endfor %}
    </div>
    {% endfor %}

    <div class="category" id="audio-summary">
        <h2>🎵 语音摘要</h2>
        <audio controls style="width: 100%; max-width: 600px;">
            <source src="../../audio/{{ audio_filename }}" type="audio/mpeg">
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

# 主页模板
INDEX_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenClaw 日报 - 主页</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
        .header { text-align: center; margin-bottom: 30px; padding: 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 10px; }
        .header h1 { margin: 0 0 10px 0; }
        .header p { margin: 5px 0; opacity: 0.9; }
        .day-card { background: white; margin: 20px 0; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .day-card h2 { color: #667eea; margin: 0 0 10px 0; font-size: 1.3em; }
        .day-card .stats { color: #666; margin: 10px 0; font-size: 0.95em; }
        .day-card .preview { margin: 15px 0; padding: 15px; background: #f9f9f9; border-radius: 6px; }
        .day-card .preview p { margin: 5px 0; color: #555; line-height: 1.6; }
        .day-card a { display: inline-block; margin-top: 15px; padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 6px; }
        .day-card a:hover { background: #5a6fd8; }
        .footer { text-align: center; margin-top: 40px; color: #999; font-size: 0.9em; }
        .empty { text-align: center; color: #999; padding: 40px 20px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>📡 OpenClaw 日报</h1>
        <p>每日自动收集 OpenClaw 生态动态</p>
        <p>共收录 <strong>{{ total_days }}</strong> 期内容，最新：{{ latest_date }}</p>
    </div>

    {% if days %}
        {% for day in days %}
        <div class="day-card">
            <h2>{{ day.date }} · {{ day.total_items }} 条动态</h2>
            <div class="stats">
                {% for cat, count in day.categories.items() %}
                    {{ category_name(cat) }} ({{ count }}) 
                {% endfor %}
            </div>
            <div class="preview">
                {% for item in day.preview_items %}
                    <p>{{ loop.index }}. {{ item }}</p>
                {% endfor %}
                {% if day.total_items > 3 %}
                    <p style="color: #999; font-style: italic;">... 还有 {{ day.total_items - 3 }} 条未显示</p>
                {% endif %}
            </div>
            <a href="public/archive/{{ day.date }}/">查看详情 →</a>
        </div>
        {% endfor %}
    {% else %}
        <div class="empty">
            <p>暂无历史内容</p>
            <p>首次运行将自动生成第一期日报</p>
        </div>
    {% endif %}

    <div class="footer">
        <p>Powered by OpenClaw + Agent Reach</p>
    </div>
</body>
</html>
"""

class PageGenerator:
    def __init__(self, output_dir="public"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.detail_template = Template(DETAIL_TEMPLATE)
        self.index_template = Template(INDEX_TEMPLATE)

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

    def generate_detail_page(self, categorized_data, date_str, audio_filename):
        """生成单日详情页（保存到 archive/YYYY-MM-DD/index.html）"""
        total = sum(len(entries) for entries in categorized_data.values())
        html = self.detail_template.render(
            date=date_str,
            categorized=categorized_data,
            category_name=self.category_name,
            total_items=total,
            audio_filename=f"../audio/{audio_filename}"  # 相对路径：从 archive/ 到 audio/
        )
        # 输出到 archive/YYYY-MM-DD/index.html
        archive_dir = self.output_dir / "archive" / date_str
        archive_dir.mkdir(parents=True, exist_ok=True)
        output_path = archive_dir / "index.html"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"✅ 详情页已生成: {output_path}")
        return str(output_path)

    def generate_index_page(self, history_metadata):
        """生成主页（汇总所有日期）"""
        # history_metadata: list of dicts with keys: date, total_items, categories, preview_items
        total_days = len(history_metadata)
        latest_date = history_metadata[0]['date'] if history_metadata else '暂无'

        html = self.index_template.render(
            total_days=total_days,
            latest_date=latest_date,
            days=history_metadata,
            category_name=self.category_name
        )
        output_path = self.output_dir / "index.html"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"✅ 主页已生成: {output_path}")
        return str(output_path)
