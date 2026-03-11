import json
from datetime import datetime
import re
from llm_providers import (
    LLMProvider,
    OpenAIProvider,
    GroqProvider,
    OpenRouterProvider,
    OllamaProvider,
    HuggingFaceProvider,
    ArceeProvider,
    FallbackProvider
)

# 受众友好的摘要改写提示（保持原来风格）
PROMPT_TEMPLATE = """请将以下内容改写成一段**简洁、易懂**的中文（30-70字），要求：
- 忠实原意，不添加不存在的信息
- 用生活化语言，避免"修复""重构""增强"等黑话
- 如果原文提到用户的好处（更安全、更方便、省时），请保留
- 如果原文偏技术，请提炼一句通俗说明
- 不要主动加入"OpenClaw""ChatGPT"等工具名（除非原文出现）

{source_text}

请严格按 **JSON 格式** 输出，只包含一个字段：
{
  "summary": "你的总结"
}

不要输出任何其他内容（包括思考过程、解释、markdown 标记）。"""

class ContentProcessor:
    def __init__(self, providers: list = None):
        """
        初始化内容处理器
        providers: 按优先级排列的 LLMProvider 列表，例如 [OpenRouterProvider(...), OllamaProvider(), FallbackProvider()]
                    如果为 None，则使用默认混合策略（不含 OpenAI/Groq）
        """
        if providers is None:
            # 默认混合策略：OpenRouter → Ollama → HuggingFace → Arcee → Fallback
            self.providers = [
                OpenRouterProvider(),
                OllamaProvider(),
                HuggingFaceProvider(),
                ArceeProvider(),
                FallbackProvider()
            ]
        else:
            self.providers = providers

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
        """使用混合策略生成摘要"""
        title = entry.get('title', '').strip()
        raw = entry.get('summary', entry.get('description', '')).strip()

        if raw and len(raw) > 20:
            content = raw
        else:
            content = ""

        # 按优先级尝试每个提供商
        last_error = None
        for provider in self.providers:
            try:
                summary = provider.summarize(title, content, PROMPT_TEMPLATE)
                # 后处理：清理可能的 ANSWER: 前缀和思考内容
                if summary:
                    # 去除 ANSWER: 前缀
                    low = summary.lower()
                    if low.startswith('answer:'):
                        summary = summary[len('answer:'):].lstrip()
                    # 如果以思考关键词开头，尝试提取最后一句
                    thinking_prefixes = ['用户', '让我', '需要', '我先', '想想', '但', '不过', '所以', '因此']
                    if any(low.startswith(kp) or summary.startswith(kp) for kp in thinking_prefixes):
                        # 找最后一个句号、问号或感叹号
                        for sep in ['。', '？', '！']:
                            idx = summary.rfind(sep)
                            if idx != -1 and idx < len(summary) - 1:
                                summary = summary[idx+1:].strip()
                                break
                print(f"✅ 摘要生成成功 ({provider.name()}: {summary[:50]}...)")
                return summary
            except Exception as e:
                print(f"⚠️ {provider.name()} 失败: {str(e)[:100]}")
                last_error = e
                continue

        # 如果全部失败（理论上不会，因为有 FallbackProvider），使用最简方式
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
    # 测试混合策略
    processor = ContentProcessor()
    with open("data/latest_cache.json", 'r', encoding='utf-8') as f:
        entries = json.load(f)
    result = processor.process_all(entries[:3])
    print(json.dumps(result, indent=2, ensure_ascii=False))