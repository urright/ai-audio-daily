import asyncio
import os
import json
from datetime import datetime
from pathlib import Path
from gtts import gTTS
import concurrent.futures

class AudioGenerator:
    def __init__(self, output_dir="public/audio"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.lang = 'zh-cn'  # gTTS语言代码
        self.slow = False  # 慢速模式
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)

    def _generate_sync(self, text, output_path):
        """同步生成单个语音文件（gTTS）"""
        try:
            tts = gTTS(text=text, lang=self.lang, slow=self.slow)
            tts.save(str(output_path))
            return str(output_path)
        except Exception as e:
            print(f"❌ gTTS error: {e}")
            return None

    async def generate_summary_audio(self, categorized_data, audio_filename=None, max_entries_per_category=5):
        """生成完整语音摘要（单一文件）
        
        Args:
            audio_filename: 可选，自定义文件名（如 2026-03-09.mp3）
        """
        print("🎵 开始生成语音...")

        # 构建完整文本
        full_text = self._build_full_text(categorized_data, max_entries_per_category)
        
        if not full_text.strip():
            print("❌ 没有内容可生成")
            return None

        # 确定文件名
        if not audio_filename:
            audio_filename = "daily_summary.mp3"
        output_path = self.output_dir / audio_filename
        
        # 生成音频
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self.thread_pool,
            self._generate_sync,
            full_text,
            output_path
        )

        if result:
            print(f"✅ 语音生成完成: {result}")
            return result
        else:
            print("❌ 语音生成失败")
            return None

    def _build_full_text(self, categorized_data, max_entries_per_category):
        """构建完整语音文本"""
        parts = []
        date_str = datetime.now().strftime("%Y年%m月%d日")
        parts.append(f"OpenClaw 生态日报，{date_str}。")
        parts.append(f"今日共收集{self._count_total_entries(categorized_data)}条动态。")
        parts.append("")  # 停顿

        for category, entries in categorized_data.items():
            if not entries:
                continue
                
            parts.append(f"【{self._category_name(category)}】")
            parts.append("")
            
            for i, entry in enumerate(entries[:max_entries_per_category]):
                summary = entry.get('short_summary', entry.get('title', ''))
                parts.append(f"第{i+1}条：{summary}")
                parts.append("")  # 条目间停顿
            
            if len(entries) > max_entries_per_category:
                parts.append(f"还有{len(entries) - max_entries_per_category}条内容未念出")
                parts.append("")
        
        parts.append("以上是今日OpenClaw动态概要，感谢收听！")
        return "\n".join(parts)

    def _count_total_entries(self, categorized_data):
        total = 0
        for entries in categorized_data.values():
            total += len(entries)
        return total

    def _category_name(self, cat):
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

    def __del__(self):
        """清理线程池"""
        self.thread_pool.shutdown(wait=True)

if __name__ == "__main__":
    # 测试
    async def test():
        with open("data/processed.json", 'r', encoding='utf-8') as f:
            categorized = json.load(f)

        generator = AudioGenerator()
        audio_file = await generator.generate_summary_audio(categorized)
        print(f"Generated: {audio_file}")

    asyncio.run(test())
