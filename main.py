#!/usr/bin/env python3
import asyncio
import json
import os
from pathlib import Path
from datetime import datetime

from collector import DataCollector
from processor import ContentProcessor
from audio_generator import AudioGenerator
from page_generator import PageGenerator
from telegram_sender import TelegramSender

class AIAudioDailyAgent:
    def __init__(self):
        self.data_dir = Path("data")
        self.public_dir = Path("public")
        self.history_dir = Path("history")
        self.history_dir.mkdir(exist_ok=True)

        # 组件
        self.collector = DataCollector()
        self.processor = ContentProcessor()
        self.audio_gen = AudioGenerator()
        self.page_gen = PageGenerator()
        self.telegram = TelegramSender()

    async def run(self):
        print("="*50)
        print("🤖 OpenClaw 日报 Agent 开始运行")
        print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*50)

        try:
            # 1. 收集数据
            entries = self.collector.collect_all()
            if not entries:
                print("❌ 没有收集到新内容，终止")
                return False

            # 2. 处理数据（总结+分类）
            categorized = self.processor.process_all(entries)
            total_items = sum(len(v) for v in categorized.values())

            # 3. 生成语音（使用日期命名）
            date_str = datetime.now().strftime("%Y-%m-%d")
            audio_filename = f"{date_str}.mp3"
            audio_file = await self.audio_gen.generate_summary_audio(
                categorized,
                audio_filename=audio_filename  # 传递自定义文件名
            )
            if not audio_file:
                print("❌ 语音生成失败")
                return False

            # 4. 保存今日数据到历史记录
            history_file = self.history_dir / f"{date_str}.json"
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'date': date_str,
                    'total_items': total_items,
                    'categories': {k: len(v) for k, v in categorized.items()},
                    'entries': categorized,
                    'audio': audio_filename,
                    'generated_at': datetime.now().isoformat()
                }, f, indent=2, ensure_ascii=False)
            print(f"✅ 历史数据已保存: {history_file}")

            # 5. 生成详情页（保存到 archive/YYYY-MM-DD/index.html）
            self.page_gen.generate_detail_page(
                categorized,
                date_str=date_str,
                audio_filename=audio_filename
            )

            # 6. 生成主页（汇总所有历史）
            await self._generate_homepage()

            # 7. 发送到Telegram（发送今日详情页链接）
            page_url = f"https://urright.github.io/ai-audio-daily/archive/{date_str}/"
            if self.telegram.bot_token and self.telegram.chat_id:
                self.telegram.send_daily_report(
                    page_url=page_url,
                    audio_path=audio_file,
                    total_items=total_items
                )
            else:
                print("⚠️ Telegram配置缺失，跳过推送")

            print("✅ 全部完成！")
            return True

        except Exception as e:
            print(f"❌ 执行出错: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def _generate_homepage(self):
        """扫描历史数据，生成主页"""
        # 读取所有历史文件
        history_files = sorted(self.history_dir.glob("*.json"), reverse=True)
        days_metadata = []

        for hist_file in history_files[:30]:  # 最多显示30天
            try:
                with open(hist_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 提取预览（每个类别取前1条）
                preview_items = []
                for cat, entries in data['categories'].items():
                    if entries > 0:
                        cat_entries = data['entries'].get(cat, [])
                        if cat_entries:
                            preview_items.append(cat_entries[0]['short_summary'])
                    if len(preview_items) >= 3:
                        break
                
                days_metadata.append({
                    'date': data['date'],
                    'total_items': data['total_items'],
                    'categories': data['categories'],
                    'preview_items': preview_items[:3]
                })
            except Exception as e:
                print(f"⚠️ 读取历史文件失败 {hist_file}: {e}")

        # 生成主页
        self.page_gen.generate_index_page(days_metadata)
        print(f"✅ 主页已更新，共 {len(days_metadata)} 期")

    def cleanup_old_files(self, days=7):
        """清理旧音频和历史数据（保留最近7天）"""
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(days=days)
        
        # 清理音频
        audio_dir = self.data_dir / "audio"
        for f in audio_dir.glob("*.mp3"):
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime < cutoff:
                f.unlink()
                print(f"🗑️ 删除音频: {f.name}")

        # 清理历史数据（保留最近7天）
        for hist_file in self.history_dir.glob("*.json"):
            mtime = datetime.fromtimestamp(hist_file.stat().st_mtime)
            if mtime < cutoff:
                hist_file.unlink()
                print(f"🗑️ 删除历史: {hist_file.name}")

if __name__ == "__main__":
    agent = AIAudioDailyAgent()
    success = asyncio.run(agent.run())
    exit(0 if success else 1)
