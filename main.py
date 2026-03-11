#!/usr/bin/env python3
import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from argparse import ArgumentParser

from collector import DataCollector
from processor import ContentProcessor, OpenAIProvider, GroqProvider, OpenRouterProvider, OllamaProvider, HuggingFaceProvider, ArceeProvider, FallbackProvider
from audio_generator import AudioGenerator
from page_generator import PageGenerator
from telegram_sender import TelegramSender

def resolve_env_vars(value):
    if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
        var_name = value[2:-1]
        return os.getenv(var_name, value)
    return value

def load_profiles(profiles_path='profiles.json'):
    with open(profiles_path, 'r', encoding='utf-8') as f:
        profiles = json.load(f)
    for p in profiles:
        p['telegram_bot_token'] = resolve_env_vars(p.get('telegram_bot_token', ''))
        p['telegram_chat_id'] = resolve_env_vars(p.get('telegram_chat_id', ''))
    return profiles

def get_selected_profile(profiles, name):
    for p in profiles:
        if p['name'] == name:
            return p
    return None

async def run_profile(profile):
    print(f"\n{'='*60}")
    print(f"🚀 开始运行 profile: {profile['name']}")
    print(f"📝 {profile['description']}")
    print(f"{'='*60}")

    base_dir = Path('.')
    config_dir = base_dir / profile['config_dir']
    output_dir = base_dir / profile['output_dir']
    audio_dir = output_dir / profile['audio_subdir']
    history_dir = base_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    output_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)

    # 1. 收集
    collector = DataCollector(config_dir=str(config_dir))
    entries = collector.collect_all()
    if not entries:
        print("❌ 没有收集到新内容，跳过此 profile")
        return False

    # 2. 处理 - 构建 providers（支持 profile 配置优先级）
    def build_providers(profile):
        provider_map = {
            'openai': lambda: OpenAIProvider(),
            'groq': lambda: GroqProvider(),
            'openrouter': lambda: OpenRouterProvider(),
            'ollama': lambda: OllamaProvider(),
            'huggingface': lambda: HuggingFaceProvider(),
            'arcee': lambda: ArceeProvider(),
        }
        default_order = ['openrouter', 'ollama', 'huggingface', 'arcee']
        order = profile.get('llm_providers', default_order)
        providers = []
        for key in order:
            if key in provider_map:
                try:
                    providers.append(provider_map[key]())
                except Exception as e:
                    print(f"⚠️ 跳过提供商 {key}: {e}")
        if not providers:
            providers = [FallbackProvider()]
        return providers

    providers = build_providers(profile)
    processor = ContentProcessor(providers=providers)
    categorized = processor.process_all(entries)
    total_items = sum(len(v) for v in categorized.values())

    # 3. 语音
    date_str = datetime.now().strftime("%Y-%m-%d")
    audio_filename = f"{date_str}.mp3"
    audio_gen = AudioGenerator(output_dir=str(audio_dir))
    audio_file = await audio_gen.generate_summary_audio(
        categorized,
        audio_filename=audio_filename
    )
    if not audio_file:
        print("❌ 语音生成失败")
        return False

    # 4. 保存历史（带 profile 命名，避免冲突）
    history_file = history_dir / f"{date_str}_{profile['name']}.json"
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump({
            'profile': profile['name'],
            'date': date_str,
            'total_items': total_items,
            'categories': {k: len(v) for k, v in categorized.items()},
            'entries': categorized,
            'audio': audio_filename
        }, f, indent=2, ensure_ascii=False)
    print(f"✅ 历史数据已保存: {history_file}")

    # 4b. 保存纯文本摘要（用于验证）
    text_summary_file = output_dir / f"{date_str}_summary.txt"
    with open(text_summary_file, 'w', encoding='utf-8') as f:
        f.write(f"📅 {date_str} - {profile['description']}\n\n")
        for cat, entries in categorized.items():
            f.write(f"== {cat} ==\n\n")
            for entry in entries:
                f.write(f"• {entry['title']}\n  {entry.get('short_summary','')}\n\n")
    print(f"✅ 文本摘要已保存: {text_summary_file}")

    # 5. 生成详情页
    page_gen = PageGenerator(output_dir=str(output_dir))
    page_gen.generate_detail_page(
        categorized,
        date_str=date_str,
        audio_filename=audio_filename
    )

    # 6. 生成主页（显示最近30期）
    await _generate_profile_homepage(page_gen, history_dir, profile['name'], output_dir)

    # 7. Telegram 推送
    telegram = TelegramSender(
        bot_token=profile['telegram_bot_token'],
        chat_id=profile['telegram_chat_id']
    )
    if telegram.bot_token and telegram.chat_id:
        repo_name = os.getenv('GITHUB_REPO_NAME', 'ai-audio-daily')
        url_path = profile.get('url_path', profile['output_dir'])
        if url_path.startswith('docs/'):
            url_path = url_path[5:]
        page_url = f"https://urright.github.io/{repo_name}/{url_path}/archive/{date_str}/"
        telegram.send_daily_report(
            page_url=page_url,
            audio_path=audio_file,
            total_items=total_items
        )
    else:
        print("⚠️ Telegram配置缺失，跳过推送")

    print(f"✅ Profile {profile['name']} 完成！")
    return True

async def _generate_profile_homepage(page_gen, history_dir, profile_name, output_dir):
    """生成 profile 的主页，显示最近30期"""
    pattern = f"*_{profile_name}.json"
    history_files = sorted(history_dir.glob(pattern), reverse=True)[:30]

    days_metadata = []
    for hist_file in history_files:
        try:
            with open(hist_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
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

    page_gen.generate_index_page(days_metadata)
    print(f"✅ 主页已更新 (profile={profile_name})，共 {len(days_metadata)} 期")

async def main():
    parser = ArgumentParser(description="OpenClaw 日报Agent (多profile版)")
    parser.add_argument('--profile', help='只运行指定的profile名称')
    args = parser.parse_args()

    try:
        profiles = load_profiles()
    except Exception as e:
        print(f"❌ 加载profiles.json失败: {e}")
        sys.exit(1)

    if args.profile:
        profile = get_selected_profile(profiles, args.profile)
        if not profile:
            print(f"❌ 未找到profile: {args.profile}")
            sys.exit(1)
        profiles_to_run = [profile]
    else:
        profiles_to_run = [p for p in profiles if p.get('enabled', True)]

    print(f"🔧 即将运行 {len(profiles_to_run)} 个 profiles: {[p['name'] for p in profiles_to_run]}")

    all_success = True
    for profile in profiles_to_run:
        success = await run_profile(profile)
        if not success:
            all_success = False
            print(f"⚠️ Profile {profile['name']} 执行失败，继续下一个...")

    print("\n" + "="*60)
    if all_success:
        print("✅ 所有 profiles 执行完成")
    else:
        print("⚠️ 部分 profiles 执行失败")
    print("="*60)

    return all_success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
