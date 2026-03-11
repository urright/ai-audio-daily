"""
混合 LLM 提供商系统
按优先级尝试多个提供商，成功则返回；全部失败则降级
"""

import openai
import requests
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import os

class LLMProvider(ABC):
    @abstractmethod
    def summarize(self, title: str, content: str, prompt_template: str) -> str:
        """生成摘要，返回文本；失败抛出异常"""
        pass

    @abstractmethod
    def name(self) -> str:
        pass

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini", base_url: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.base_url = base_url
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client

    def name(self) -> str:
        return f"openai:{self.model}"

    def summarize(self, title: str, content: str, prompt_template: str) -> str:
        source_text = f"标题：{title}\n原文：{content}" if content else f"标题：{title}"
        prompt = prompt_template + "\n\n" + source_text
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=150
        )
        return response.choices[0].message.content.strip().strip('"').strip()

class GroqProvider(LLMProvider):
    def __init__(self, api_key: str = None, model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model
        self.base_url = "https://api.groq.com/openai/v1"

    def name(self) -> str:
        return f"groq:{self.model}"

    def summarize(self, title: str, content: str, prompt_template: str) -> str:
        client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
        source_text = f"标题：{title}\n原文：{content}" if content else f"标题：{title}"
        prompt = prompt_template + "\n\n" + source_text
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=150
        )
        message = response.choices[0].message
        text = message.content
        if text is None:
            # StepFun/某些推理模型：实际输出在 reasoning 字段
            try:
                # 优先从 model_dump 获取
                dump = message.model_dump()
                text = dump.get('reasoning') or dump.get('reasoning_details', [{}])[0].get('text', '')
            except Exception:
                text = ""
        return text.strip().strip('"').strip()

class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.3"):
        self.base_url = base_url.rstrip('/')
        self.model = model

    def name(self) -> str:
        return f"ollama:{self.model}"

    def summarize(self, title: str, content: str, prompt_template: str) -> str:
        source_text = f"标题：{title}\n原文：{content}" if content else f"标题：{title}"
        prompt = prompt_template + "\n\n" + source_text
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.5}
        }
        resp = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json()["response"].strip().strip('"').strip()

class HuggingFaceProvider(LLMProvider):
    def __init__(self, api_key: str = None, model: str = "google/flan-t5-large"):
        self.api_key = api_key or os.getenv("HF_API_KEY")
        self.model = model
        self.base_url = f"https://api-inference.huggingface.co/models/{model}"

    def name(self) -> str:
        return f"hf:{self.model}"

    def summarize(self, title: str, content: str, prompt_template: str) -> str:
        source_text = f"标题：{title}\n原文：{content}" if content else f"标题：{title}"
        prompt = prompt_template + "\n\n" + source_text
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        payload = {"inputs": prompt, "parameters": {"max_length": 150, "temperature": 0.5}}
        resp = requests.post(self.base_url, json=payload, headers=headers, timeout=120)
        resp.raise_for_status()
        result = resp.json()
        # HuggingFace 返回格式多样，常见为 [{"generated_text": "..."}]
        if isinstance(result, list) and "generated_text" in result[0]:
            return result[0]["generated_text"].strip()
        elif isinstance(result, dict) and "generated_text" in result:
            return result["generated_text"].strip()
        else:
            raise ValueError(f"Unexpected HF response: {result}")

class OpenRouterProvider(LLMProvider):
    def __init__(self, api_key: str = None, model: str = "stepfun/step-3.5-flash:free"):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1"

    def name(self) -> str:
        return f"openrouter:{self.model}"

    def summarize(self, title: str, content: str, prompt_template: str) -> str:
        client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
        source_text = f"标题：{title}\n原文：{content}" if content else f"标题：{title}"
        prompt = prompt_template + "\n\n" + source_text
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=150,
            extra_headers={
                "HTTP-Referer": "https://github.com/urright/mydailyaudio",
                "X-Title": "MyDailyAudio"
            }
        )
        message = response.choices[0].message
        text = message.content
        if text is None:
            # StepFun/某些推理模型：实际输出在 reasoning 字段
            try:
                dump = message.model_dump()
                text = dump.get('reasoning') or ''
            except Exception:
                text = ""
        return text.strip().strip('"').strip()

class ArceeProvider(LLMProvider):
    """Arcee Trinity Large via OpenRouter (free tier)"""
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.model = "arcee-ai/trinity-large-preview:free"
        self.base_url = "https://openrouter.ai/api/v1"

    def name(self) -> str:
        return f"arcee:{self.model}"

    def summarize(self, title: str, content: str, prompt_template: str) -> str:
        client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
        source_text = f"标题：{title}\n原文：{content}" if content else f"标题：{title}"
        prompt = prompt_template + "\n\n" + source_text
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=150,
            extra_headers={
                "HTTP-Referer": "https://github.com/urright/mydailyaudio",
                "X-Title": "MyDailyAudio"
            }
        )
        message = response.choices[0].message
        text = message.content
        if text is None:
            try:
                dump = message.model_dump()
                text = dump.get('reasoning') or ''
            except Exception:
                text = ""
        return text.strip().strip('"').strip()

class FallbackProvider(LLMProvider):
    """最后降级：返回原摘要或简化的标题"""
    def __init__(self):
        pass

    def name(self) -> str:
        return "fallback:raw"

    def summarize(self, title: str, content: str, prompt_template: str) -> str:
        if content and len(content) > 20:
            return content[:150] + "..."
        # 清理标题前缀
        import re
        cleaned = re.sub(r'^(fix|feat|feature|refactor|chore|test|docs|style|perf|build|ci|security|release|announce):\s*', '', title, flags=re.IGNORECASE)
        return cleaned[:80] if cleaned else title[:80]
