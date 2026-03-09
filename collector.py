import feedparser
import yt_dlp
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

class DataCollector:
    def __init__(self, config_dir="config"):
        self.config_dir = Path(config_dir)
        self.rss_feeds = self._load_rss_feeds(self.config_dir / "rss_feeds.txt")
        self.youtube_channels = self._load_channels(self.config_dir / "channels.txt")
        self.cache_file = Path("data/latest_cache.json")
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        Path("data").mkdir(exist_ok=True)
        Path("data/audio").mkdir(exist_ok=True)
        Path("data/text").mkdir(exist_ok=True)

    def _load_rss_feeds(self, filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]

    def _load_channels(self, filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]

    def collect_rss(self, hours_back=24):
        """收集24小时内的RSS文章"""
        entries = []
        cutoff = datetime.now() - timedelta(hours=hours_back)

        for feed_url in self.rss_feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries:
                    published = entry.get('published_parsed') or entry.get('updated_parsed')
                    if published:
                        pub_date = datetime(*published[:6])
                        if pub_date > cutoff:
                            entries.append({
                                'source': 'rss',
                                'title': entry.get('title', 'No title'),
                                'link': entry.get('link', ''),
                                'summary': entry.get('summary', entry.get('description', '')),
                                'published': pub_date.isoformat(),
                                'category': self._guess_category(entry)
                            })
            except Exception as e:
                print(f"❌ RSS fetch error {feed_url}: {e}")

        return entries

    def collect_youtube_audio(self, max_videos_per_channel=5):
        """收集YouTube音频信息（仅元数据，不下载）"""
        entries = []

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'force_generic_extractor': False
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            for channel_url in self.youtube_channels:
                try:
                    info = ydl.extract_info(channel_url, download=False)
                    if 'entries' in info:
                        videos = info['entries'][:max_videos_per_channel]
                        for video in videos:
                            if video:
                                entries.append({
                                    'source': 'youtube',
                                    'title': video.get('title', 'No title'),
                                    'url': video.get('url', video.get('webpage_url', '')),
                                    'duration': video.get('duration', 0),
                                    'uploader': video.get('uploader', ''),
                                    'upload_date': video.get('upload_date', ''),
                                    'category': self._guess_category(video)
                                })
                except Exception as e:
                    print(f"❌ YouTube error {channel_url}: {e}")

        return entries

    def _guess_category(self, item):
        """OpenClaw 相关分类"""
        title = item.get('title', '').lower()
        summary = item.get('summary', item.get('description', '')).lower()
        text = title + ' ' + summary

        categories = {
            'release': ['release', 'v1.0', 'v2.0', 'version', 'update', 'changelog'],
            'feature': ['feature', 'new', 'add', 'improve', 'enhance', 'support'],
            'tutorial': ['how to', 'tutorial', 'guide', 'learn', 'introduction', 'getting started', 'quickstart'],
            'discussion': ['discussion', 'community', 'forum', 'idea', 'feedback', 'suggestion'],
            'skill': ['skill', 'agent', 'tool', 'integration', 'plugin', 'extension'],
            'bugfix': ['bug', 'fix', 'issue', 'problem', 'error', 'crash'],
            'announcement': ['announcement', 'news', 'blog', 'post', 'article']
        }

        for cat, keywords in categories.items():
            if any(kw in text for kw in keywords):
                return cat
        return 'general'

    def collect_all(self):
        """收集所有来源"""
        print("🚀 开始收集数据...")
        rss_entries = self.collect_rss()
        youtube_entries = self.collect_youtube_audio()
        all_entries = rss_entries + youtube_entries

        # 去重（按标题）
        seen = set()
        unique = []
        for entry in all_entries:
            title = entry['title'][:100]
            if title not in seen:
                seen.add(title)
                unique.append(entry)

        # 保存缓存
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(unique, f, indent=2, ensure_ascii=False)

        print(f"✅ 收集完成，共 {len(unique)} 条内容")
        return unique

if __name__ == "__main__":
    collector = DataCollector()
    entries = collector.collect_all()
    print(f"Total entries: {len(entries)}")
