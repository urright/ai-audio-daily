import openai
from dotenv import load_dotenv
import os
import json
from datetime import datetime
import re

load_dotenv()

class ContentProcessor:
    def __init__(self, api_key=None, model=None, use_groq=False):
        if use_groq or os.getenv('GROQ_API_KEY'):
            self.client = openai.OpenAI(
                api_key=api_key or os.getenv('GROQ_API_KEY'),
                base_url="https://api.groq.com/openai/v1"
            )
            self.model = model or "llama-3.3-70b-versatile"
            self.provider = "groq"
        else:
            self.client = openai.OpenAI(api_key=api_key or os.getenv('OPENAI_API_KEY'))
            self.model = model or "gpt-4o-mini"
            self.provider = "openai"

    def parse_date(self, entry):
        date_str = entry.get('published')
        if not date_str:
            return datetime.min
        try:
            if 'T' in date_str:
                return datetime.fromisoformat(date_str.replace('Z', ''))
            return datetime.strptime(date_str[:10], '%Y-%m-%d')
        except:
            return datetime.min

    def is_high_value(self, entry):
        """判断条目是否对普通听众有价值（应被保留）。"""
        if entry.get('source') == 'youtube':
            return True

        title = entry.get('title', '').lower().strip()

        # 前缀白名单（这些特征强烈表明有价值）
        valuable_prefixes = [
            'feat', 'feature', 'release', 'security', 'announce', 'announcement',
            'video', 'tutorial', 'guide', 'docs:', 'breaking'
        ]
        for prefix in valuable_prefixes:
            if title.startswith(prefix):
                return True

        # fix 类：只保留涉及安全问题或用户可见严重问题
        if title.startswith('fix'):
            impact_keywords = [
                'security', 'vulnerability', 'crash', 'error', 'bug',
                'issue', 'breach', 'leak', 'bypass', 'fail', 'loss',
                'incorrect', 'wrong', 'critical', 'important', 'user',
                'data loss', 'authentication', 'authorization'
            ]
            text = title + ' ' + entry.get('summary', '')
            if any(kw in text.lower() for kw in impact_keywords):
                return True
            else:
                return False

        # 标题中是否包含高价值动词（作为独立单词）
        value_pattern = re.compile(
            r'\b(?:new|add|introduce|support|improve|enhance|update|upgrade|launch|publish|announce|release|available)\b',
            re.IGNORECASE
        )
        if value_pattern.search(title):
            return True

        # 低价值特征一旦命中直接拒绝
        low_value_indicators = [
            'refactor', 'chore:', 'ci:', 'test:', 'docs:', 'typo', 'format', 'lint',
            'deps', 'bump', 'build:', 'auto', 'bot', 'workflow', 'github actions',
            'update readme', 'update .gitignore', 'update license', 'update changelog',
            'version bump', 'prepare for release', 'infra', 'extract', 'compile',
            'pin', 'unify', 'simplify', 'split', 'rename', 'clarify', 'hack', 'wip',
            'todo', 'minor', 'merge ', 'style'
        ]
        for lv in low_value_indicators:
            if lv in title:
                return False

        if len(title) < 12 and not entry.get('summary'):
            return False

        if re.match(r'^[^\w\s]+$', title):
            return False

        # 其余不确定的视为低价值（宁可错杀，不放过噪音）
        return False

    def summarize(self, entry):
        """生成忠实于原文的通俗摘要，避免强行植入品牌"""
        title = entry.get('title', '').strip()
        raw = entry.get('summary', entry.get('description', '')).strip()

        if raw and len(raw) > 20:
            source_text = f"标题：{title}\n原文：{raw}"
        else:
            source_text = f"标题：{title}"

        prompt = f"""请将以下内容改写成一段**简洁、易懂**的中文（30-70字），要求：
- 忠实原意，不添加不存在的信息
- 用生活化语言，避免“修复”“重构”“增强”等黑话
- 如果原文提到用户的好处（更安全、更方便、省时），请保留
- 如果原文偏技术，请提炼一句通俗说明
- 不要主动加入“OpenClaw”“ChatGPT”等工具名（除非原文出现）

{source_text}

直接输出改写后的摘要："""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=150
            )
            summary = response.choices[0].message.content.strip().strip('"').strip()
            return summary if summary else self._simple_fallback(title)
        except Exception as e:
            print(f"❌ Summarize error: {e}")
            return self._simple_fallback(title)

    def _simple_fallback(self, title):
        cleaned = re.sub(r'^(fix|feat|feature|refactor|chore|test|docs|style|perf|build|ci|security|release|announce):\s*', '', title, flags=re.IGNORECASE)
        return cleaned[:80] if cleaned else "OpenClaw 更新"

    def categorize(self, entry):
        title = entry.get('title', '').lower()
        if entry.get('source') == 'youtube':
            return 'general'
        if 'security' in title or 'vulnerability' in title:
            return 'bugfix'
        if title.startswith('feat') or title.startswith('feature'):
            return 'feature'
        if title.startswith('release'):
            return 'release'
        if title.startswith('fix'):
            return 'bugfix'
        return entry.get('category', 'general')

    def process_all(self, entries):
        print("🔧 开始处理内容...")
        valuable = [e for e in entries if self.is_high_value(e)]
        removed = len(entries) - len(valuable)
        print(f"  ⚠️  过滤掉 {removed} 条低价值内容，保留 {len(valuable)} 条")

        processed = []
        for i, entry in enumerate(valuable):
            print(f"  [{i+1}/{len(valuable)}] 处理: {entry['title'][:50]}...")
            if 'published' not in entry:
                if 'upload_date' in entry and entry['upload_date']:
                    date_str = entry['upload_date']
                    if len(date_str) == 8:
                        entry['published'] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
                    else:
                        entry['published'] = date_str
                else:
                    entry['published'] = datetime.now().strftime("%Y-%m-%d")
            if 'link' not in entry and 'url' in entry:
                entry['link'] = entry['url']
            elif 'link' not in entry:
                entry['link'] = '#'
            entry['_dt'] = self.parse_date(entry)
            entry['short_summary'] = self.summarize(entry)
            entry['category'] = self.categorize(entry)
            processed.append(entry)

        categorized = {}
        for entry in processed:
            cat = entry['category']
            categorized.setdefault(cat, []).append(entry)

        MAX_PER_CATEGORY = 3
        for cat, ents in categorized.items():
            ents.sort(key=lambda e: e['_dt'], reverse=True)
            categorized[cat] = ents[:MAX_PER_CATEGORY]
            for e in categorized[cat]:
                if '_dt' in e:
                    del e['_dt']

        total_after = sum(len(v) for v in categorized.values())
        print(f"✅ 处理完成，保留 {total_after} 条（每类最多 {MAX_PER_CATEGORY} 条），共 {len(categorized)} 个类别")
        return categorized

if __name__ == "__main__":
    with open("data/latest_cache.json", 'r', encoding='utf-8') as f:
        entries = json.load(f)
    processor = ContentProcessor()
    result = processor.process_all(entries[:3])
    print(json.dumps(result, indent=2, ensure_ascii=False))
