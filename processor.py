import openai
from dotenv import load_dotenv
import os
import json
from datetime import datetime

load_dotenv()

class ContentProcessor:
    def __init__(self, api_key=None, model=None, use_groq=False):
        # 决定使用哪种API
        if use_groq or os.getenv('GROQ_API_KEY'):
            # 使用Groq（OpenAI兼容接口）
            self.client = openai.OpenAI(
                api_key=api_key or os.getenv('GROQ_API_KEY'),
                base_url="https://api.groq.com/openai/v1"
            )
            self.model = model or "llama-3.3-70b-versatile"  # Groq当前推荐免费模型
            self.provider = "groq"
        else:
            # 使用OpenAI
            self.client = openai.OpenAI(api_key=api_key or os.getenv('OPENAI_API_KEY'))
            self.model = model or "gpt-4o-mini"
            self.provider = "openai"

    def summarize(self, entry, max_words=60):
        """为单个条目生成简短摘要（面向普通听众，突出价值与吸引力）"""
        prompt = f"""将以下AI办公自动化内容改写成一段**通俗易懂、有趣、有亮点**的中文摘要（40~80字），面向非技术背景的普通听众。突出：
- 这对普通人有什么好处？（效率提升、省时省力、自动化便利）
- 用了什么工具/产品（如OpenClaw、ChatGPT、Edge-TTS等）要自然带入
- 避免技术术语（如“修复”“重构”“增强”），用生活化表达（如“更好用”“更安全”“更方便”）

标题：{entry['title']}
原文摘要：{entry.get('summary', entry.get('description', ''))}

示例风格：
- 原：“修复Telegram连接稳定性问题” → 改：“OpenClaw 的 Telegram 机器人现在更稳定，消息不会漏掉啦！”
- 原：“发布新版支持多语言” → 改：“工具现在支持中文，用起来更顺手！”

请直接输出改写后的摘要，不要额外说明："""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,  # 增加创造性
                max_tokens=200
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"❌ Summarize error: {e}")
            # fallback：用简短标题
            return self._fallback_summary(entry['title'])

    def _fallback_summary(self, title):
        """回退：将技术性标题转换为简单说明"""
        # 简单的关键词替换示例
        simple = title
        replacements = {
            'fix': '修复',
            'refactor': '优化',
            'security': '安全',
            'harden': '加固',
            'unify': '统一',
            'extract': '提取',
            'pin': '固定',
            'restrict': '限制',
            'enforce': '强制',
            'avoid': '避免',
            'remove': '移除',
            'stale': '过时',
            'cron': '定时任务',
            'deadlock': '死锁',
            'Infra': '基础设施',
        }
        for eng, ch in replacements.items():
            simple = simple.replace(eng, ch)
        return simple[:80] if simple else "OpenClaw 更新"

    def categorize(self, entry):
        """使用LLM进行精确分类（可选增强）"""
        # 暂时使用关键词分类结果
        return entry.get('category', 'general')

    def process_all(self, entries):
        """批量处理"""
        print("🔧 开始处理内容...")
        processed = []

        for i, entry in enumerate(entries):
            print(f"  [{i+1}/{len(entries)}] 处理: {entry['title'][:50]}...")
            # 标准化字段
            # 1. published
            if 'published' not in entry:
                if 'upload_date' in entry and entry['upload_date']:
                    date_str = entry['upload_date']
                    if len(date_str) == 8:
                        entry['published'] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
                    else:
                        entry['published'] = date_str
                else:
                    entry['published'] = datetime.now().strftime("%Y-%m-%d")
            
            # 2. link (统一链接字段)
            if 'link' not in entry and 'url' in entry:
                entry['link'] = entry['url']
            elif 'link' not in entry:
                entry['link'] = '#'
            
            entry['short_summary'] = self.summarize(entry)
            entry['category'] = self.categorize(entry)
            processed.append(entry)

        # 按类别分组
        categorized = {}
        for entry in processed:
            cat = entry['category']
            categorized.setdefault(cat, []).append(entry)

        # 保存处理结果
        with open("data/processed.json", 'w', encoding='utf-8') as f:
            json.dump(categorized, f, indent=2, ensure_ascii=False)

        print(f"✅ 处理完成，共 {len(processed)} 条，{len(categorized)} 个类别")
        return categorized

if __name__ == "__main__":
    # 测试
    with open("data/latest_cache.json", 'r', encoding='utf-8') as f:
        entries = json.load(f)

    processor = ContentProcessor()
    result = processor.process_all(entries[:3])  # 测试前3条
    print(json.dumps(result, indent=2, ensure_ascii=False))
