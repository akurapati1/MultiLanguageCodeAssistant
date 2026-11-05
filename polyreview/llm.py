"""Provider-agnostic chat client built on the standard library only.

Resolution order: ``LLM_PROVIDER`` env var (anthropic | openai | ollama | mock),
otherwise auto-detect from API keys, otherwise a deterministic offline mock.
Every project treats the LLM as an *enhancement*: if ``llm.available`` is False
the pure-Python logic still produces a complete result.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable, Optional


class LLMError(RuntimeError):
    pass


def _post(url: str, payload: dict, headers: dict, timeout: float = 60.0) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", **headers}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:  # pragma: no cover - network
        raise LLMError(f"HTTP {exc.code}: {exc.read().decode()[:300]}") from exc
    except urllib.error.URLError as exc:  # pragma: no cover - network
        raise LLMError(f"connection failed: {exc.reason}") from exc


@dataclass
class LLM:
    name: str = "mock"
    available: bool = False

    def complete(self, prompt: str, system: str = "", max_tokens: int = 800) -> str:
        raise NotImplementedError


class MockLLM(LLM):
    """Offline stand-in. Optionally wraps a handler so tests can script replies."""

    def __init__(self, handler: Optional[Callable[[str, str], str]] = None):
        super().__init__(name="mock", available=handler is not None)
        self.handler = handler
        self.calls: list[tuple[str, str]] = []

    def complete(self, prompt: str, system: str = "", max_tokens: int = 800) -> str:
        self.calls.append((system, prompt))
        if self.handler is None:
            raise LLMError("no LLM configured (set ANTHROPIC_API_KEY, OPENAI_API_KEY or LLM_PROVIDER=ollama)")
        return self.handler(system, prompt)


class AnthropicLLM(LLM):
    def __init__(self, api_key: str, model: str):
        super().__init__(name=f"anthropic:{model}", available=True)
        self.api_key, self.model = api_key, model

    def complete(self, prompt: str, system: str = "", max_tokens: int = 800) -> str:
        data = _post(
            os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com") + "/v1/messages",
            {"model": self.model, "max_tokens": max_tokens, "system": system,
             "messages": [{"role": "user", "content": prompt}]},
            {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
        )
        return "".join(b.get("text", "") for b in data.get("content", []))


class OpenAICompatLLM(LLM):
    """OpenAI, Groq, OpenRouter, vLLM, LM Studio, Ollama's /v1 endpoint..."""

    def __init__(self, base_url: str, api_key: str, model: str, label: str = "openai"):
        super().__init__(name=f"{label}:{model}", available=True)
        self.base_url, self.api_key, self.model = base_url.rstrip("/"), api_key, model

    def complete(self, prompt: str, system: str = "", max_tokens: int = 800) -> str:
        msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
        data = _post(f"{self.base_url}/chat/completions",
                     {"model": self.model, "messages": msgs, "max_tokens": max_tokens},
                     {"Authorization": f"Bearer {self.api_key}"})
        return data["choices"][0]["message"]["content"]


def get_llm(handler: Optional[Callable[[str, str], str]] = None) -> LLM:
    provider = os.getenv("LLM_PROVIDER", "").lower()
    model = os.getenv("LLM_MODEL", "")
    if provider == "mock" or (not provider and not any(
            os.getenv(k) for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY"))):
        return MockLLM(handler)
    if provider == "ollama":
        return OpenAICompatLLM(os.getenv("OLLAMA_URL", "http://localhost:11434/v1"), "ollama",
                               model or "llama3.1", "ollama")
    if provider == "openai" or (not provider and os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY")):
        return OpenAICompatLLM(os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                               os.getenv("OPENAI_API_KEY", ""), model or "gpt-4o-mini")
    return AnthropicLLM(os.getenv("ANTHROPIC_API_KEY", ""), model or "claude-sonnet-5-5")
