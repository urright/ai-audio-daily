# OpenClaw 日报 Agent

每天自动收集 OpenClaw 生态的相关动态（版本发布、新功能、教程、社区讨论等），分类整合后生成语音摘要，并通过 Telegram 发送到群组。

## 功能特性

- 📰 **多渠道收集**：RSS订阅、GitHub Releases、YouTube/B站元数据
- 🤖 **智能总结**：使用 Groq llama-3.3-70b-versatile 生成短摘要
- 🗂️ **自动分类**：发布、功能、教程、讨论、技能、修复、公告
- 🎵 **语音合成**：gTTS 中文语音（无需虚拟显示）
- 📄 **HTML页面**：详情页面，分类展示所有资源
- 📢 **Telegram推送**：每日语音简报 + 页面链接

## 项目结构

```
ai-audio-daily/
├── collector.py         # 数据收集
├── processor.py         # 内容处理（总结+分类）
├── audio_generator.py  # 语音合成
├── page_generator.py   # HTML页面生成
├── telegram_sender.py  # Telegram推送
├── main.py             # 主程序
├── config/
│   ├── rss_feeds.txt  # RSS源列表
│   └── channels.txt   # YouTube/B站频道
├── data/
│   ├── raw.json       # 原始数据缓存
│   ├── processed.json # 处理后数据
│   └── audio/         # 生成的语音文件
├── public/
│   └── index.html     # 生成的页面
├── scripts/
│   └── deploy.sh      # 部署脚本
├── .env                # 环境变量（需配置）
├── requirements.txt   # Python依赖
└── README.md
```

## 快速开始

### 1. 环境准备

```bash
# 已创建虚拟环境并安装依赖
cd ~/ai-audio-daily
source venv/bin/activate
```

### 2. 配置环境变量

编辑 `.env` 文件：

```bash
OPENAI_API_KEY=your-openai-api-key
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_GROUP_ID=your-group-id
```

### 3. 配置数据源

- 编辑 `config/rss_feeds.txt` 添加/修改RSS源
- 编辑 `config/channels.txt` 添加YouTube频道

### 4. 测试运行

```bash
# 测试数据收集
python collector.py

# 测试完整流程（需要配置API key）
python main.py
```

### 5. 自动部署

```bash
# 手动运行
./scripts/deploy.sh

# 或添加到cron每天8点运行
0 8 * * * cd /home/jeremy/ai-audio-daily && ./scripts/deploy.sh >> /home/jeremy/ai-audio-daily/logs/cron.log 2>&1
```

## 配置说明

### OpenAI API

本项目使用 `gpt-4o-mini` 进行内容总结，成本极低（每千次token约$0.02）。需在 [OpenAI Platform](https://platform.openai.com) 获取API Key。

### Telegram Bot

1. 在Telegram搜索 @BotFather 创建Bot，获取 Token
2. 将Bot添加到你想要的群组，并赋予发送消息权限
3. 获取群组ID：在群组发送任意消息，然后访问：
   ```
   https://api.telegram.org/bot<你的Token>/getUpdates
   ```
   在返回的JSON中找到 `chat.id`（负数表示群组）

### GitHub Pages（可选）

用于托管HTML页面：

1. 在GitHub创建仓库 `ai-audio-daily`
2. 在仓库设置中启用 GitHub Pages（源选择 `gh-pages` 分支或 `docs` 文件夹）
3. 修改 `main.py` 中的 `_deploy_page_github_pages` 方法，确保git配置正确

## 技术方案对比

### 语音合成方案

| 方案 | 成本 | 质量 | 推荐度 |
|------|------|------|--------|
| edge-tts | 免费 | ⭐⭐⭐⭐⭐ | ✅ 首选 |
| pyttsx3 | 免费 | ⭐⭐ | 备用 |
| gTTS | 免费 | ⭐⭐⭐ | 备选 |
| Azure/e11 | 付费 | ⭐⭐⭐⭐⭐ | 不推荐 |

### 页面托管方案

| 方案 | 成本 | 速度 | 推荐度 |
|------|------|------|--------|
| GitHub Pages | 免费 | 快 | ✅ 首选 |
| Vercel | 免费 | 极快 | ✅ 备选 |
| Cloudflare Pages | 免费 | 快 | ✅ |

## 故障排除

### edge-tts 在Linux下报错

需要在无头环境运行：
```bash
# 安装xvfb
sudo apt install xvfb

# 使用xvfb-run包装执行
xvfb-run -a python main.py
```

或修改 `audio_generator.py` 添加：
```python
import os
os.environ['DISPLAY'] = ':99'  # 或使用虚拟显示
```

### Telegram Bot 无响应

- 确认Bot Token正确
- 确认Bot已在群组中（发送 `/start` 到Bot）
- 确认群组ID正确（负数）
- 检查Bot是否有发送消息权限

## 后续优化方向

- [ ] 加入播客（Podcast）源
- [ ] 支持多语言语音合成
- [ ] 添加用户订阅功能（个性化分类）
- [ ] 视频自动转录（ Whisper）
- [ ] 加入更多AI工具评测来源

## 许可证

MIT

---

**现在项目基础结构已就绪，等待配置API Key和Telegram信息即可运行！** 🚀
