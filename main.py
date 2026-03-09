#!/usr/bin/env python3
import asyncio
import json
import os
import subprocess
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

        # 组件
        self.collector = DataCollector()
        self.processor = ContentProcessor()
        self.audio_gen = AudioGenerator()
        self.page_gen = PageGenerator()
        self.telegram = TelegramSender()

    async def run(self):
        print("="*50)
        print("🤖 AI 办公自动化日报 Agent 开始运行")
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

            # 3. 生成语音
            audio_file = await self.audio_gen.generate_summary_audio(categorized)
            if not audio_file:
                print("❌ 语音生成失败")
                return False

            # 4. 生成HTML页面
            page_file = self.page_gen.generate(
                categorized,
                audio_filename=Path(audio_file).name,
                output_path=str(self.public_dir / "index.html")
            )

            # 5. 计算总数
            total = sum(len(v) for v in categorized.values())

            # 6. 部署页面（GitHub Pages）
            page_url = await self._deploy_page_github_pages(page_file)
            if not page_url:
                print("⚠️ 部署失败，使用本地路径")
                page_url = f"file://{os.path.abspath(page_file)}"

            # 7. 发送到Telegram
            if self.telegram.bot_token and self.telegram.chat_id:
                self.telegram.send_daily_report(
                    page_url=page_url,
                    audio_path=audio_file,
                    total_items=total
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

    async def _deploy_page_github_pages(self, html_path):
        """部署到GitHub Pages（需要预先配置git）"""
        try:
            # 方案：git add/commit/push 到 gh-pages 分支或 docs 文件夹
            repo_dir = Path(".").resolve()
            subprocess.run(["git", "add", html_path], check=True, cwd=repo_dir)
            subprocess.run(["git", "commit", "-m", f"Update daily report {datetime.now().date()}"],
                          check=False, cwd=repo_dir)  # 可能没有变化
            subprocess.run(["git", "push"], check=False, cwd=repo_dir)
            print("✅ 页面已推送到GitHub")

            # 返回 GitHub Pages URL（需要你替换为实际仓库地址）
            # 格式：https://你的用户名.github.io/仓库名/
            return "https://你的用户名.github.io/ai-audio-daily/"
        except Exception as e:
            print(f"⚠️ GitHub部署跳过: {e}")
            return None

    def cleanup_old_files(self, days=7):
        """清理旧音频（保留最近7天）"""
        from datetime import datetime, timedelta
        audio_dir = self.data_dir / "audio"
        cutoff = datetime.now() - timedelta(days=days)

        for f in audio_dir.glob("*.mp3"):
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime < cutoff:
                f.unlink()
                print(f"🗑️ 删除旧文件: {f.name}")

if __name__ == "__main__":
    agent = AIAudioDailyAgent()
    success = asyncio.run(agent.run())
    exit(0 if success else 1)
