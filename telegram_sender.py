import os
import requests
from dotenv import load_dotenv

load_dotenv()

class TelegramSender:
    def __init__(self, bot_token=None, chat_id=None):
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or os.getenv('TELEGRAM_GROUP_ID')
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

    def send_audio(self, audio_path, caption=None):
        """发送语音消息到群组"""
        if not self.bot_token or not self.chat_id:
            print("❌ Telegram配置缺失")
            return None

        url = f"{self.base_url}/sendAudio"
        try:
            with open(audio_path, 'rb') as audio:
                files = {'audio': audio}
                data = {
                    'chat_id': self.chat_id,
                    'caption': caption or '📢 AI办公自动化日报 - 语音摘要',
                    'parse_mode': 'HTML'
                }
                resp = requests.post(url, files=files, data=data, timeout=30)

            if resp.status_code == 200:
                print("✅ 语音消息已发送")
                return resp.json()
            else:
                print(f"❌ 发送失败: {resp.status_code} {resp.text}")
                return None
        except Exception as e:
            print(f"❌ 发送异常: {e}")
            return None

    def send_message(self, text, parse_mode='HTML'):
        """发送文本消息（带链接）"""
        if not self.bot_token or not self.chat_id:
            print("❌ Telegram配置缺失")
            return None

        url = f"{self.base_url}/sendMessage"
        data = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': parse_mode,
            'disable_web_page_preview': False
        }
        try:
            resp = requests.post(url, json=data, timeout=10)
            if resp.status_code == 200:
                print("✅ 消息已发送")
                return resp.json()
            else:
                print(f"❌ 发送失败: {resp.text}")
                return None
        except Exception as e:
            print(f"❌ 发送异常: {e}")
            return None

    def send_daily_report(self, page_url, audio_path, total_items):
        """发送每日报告"""
        # 1. 发送语音摘要
        audio_result = self.send_audio(audio_path)

        # 2. 发送详情页面链接
        page_link = f"📋 <a href='{page_url}'>查看详细图文报告</a>"
        self.send_message(f"{page_link}\n\n📊 今日共收集 {total_items} 条AI自动化资讯")

if __name__ == "__main__":
    # 测试
    sender = TelegramSender()
    result = sender.send_message("测试消息：AI日报Agent运行正常")
    print(result)
