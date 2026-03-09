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
        """为单个条目生成简短摘要"""
        prompt = f"""请为以下AI办公自动化相关内容生成一个简洁的中文摘要（{max_words}字以内），突出核心信息：

标题：{entry['title']}
原文摘要：{entry.get('summary', entry.get('description', ''))}

要求：
- 简洁明了，突出重点
- 包含关键工具/产品名称
- 如果是新闻，包含事件要素
- 如果是教程，包含核心技术点

摘要："""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=120
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"❌ Summarize error: {e}")
            return entry['title']  # fallback

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
