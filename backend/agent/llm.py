from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator, List, Optional
import time

from backend.config import settings
from backend.logger import get_logger

logger = get_logger("llm")


@dataclass
class ChatMessage:
    """A single conversation turn message."""
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMChunk:
    """A streamed token chunk from the LLM."""
    text: str
    is_final: bool = False
    total_text: str = ""
    duration_ms: float = 0.0
    ttft_ms: float = 0.0


class LLMProvider(ABC):
    """Abstract Base Class for LLM providers."""

    @abstractmethod
    async def generate_stream(self, messages: List[ChatMessage]) -> AsyncIterator[LLMChunk]:
        """Streams LLM token chunks given a conversation history."""
        pass


class GroqLLMProvider(LLMProvider):
    """
    LLM provider using the Groq API (Llama-3 family) for ultra-low TTFT streaming.
    Requires GROQ_API_KEY in environment.
    """

    def __init__(self, model: str = "llama-3.1-8b-instant", api_key: str = ""):
        import httpx
        self.model = model
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)
        logger.info(f"Initialized GroqLLMProvider with model '{model}'")

    async def generate_stream(self, messages: List[ChatMessage]) -> AsyncIterator[LLMChunk]:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
            "max_tokens": 256,
            "temperature": 0.7,
        }

        t0 = time.time()
        ttft_ms = None
        accumulated = ""

        async with self.client.stream("POST", url, json=payload, headers=headers) as response:
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    import json
                    data = json.loads(data_str)
                    delta = data["choices"][0]["delta"].get("content", "")
                    if delta:
                        if ttft_ms is None:
                            ttft_ms = round((time.time() - t0) * 1000, 1)
                            logger.info(f"LLM TTFT: {ttft_ms}ms")
                        accumulated += delta
                        yield LLMChunk(text=delta, is_final=False, total_text=accumulated, ttft_ms=ttft_ms or 0)
                except Exception:
                    continue

        total_ms = round((time.time() - t0) * 1000, 1)
        logger.info(f"LLM generation complete: '{accumulated[:60]}...' ({total_ms}ms, TTFT={ttft_ms}ms)")
        yield LLMChunk(text="", is_final=True, total_text=accumulated, duration_ms=total_ms, ttft_ms=ttft_ms or 0)


class OpenAILLMProvider(LLMProvider):
    """
    LLM provider using the OpenAI API.
    Compatible with any OpenAI-spec API (OpenAI, OpenRouter, local Ollama, etc).
    Requires OPENAI_API_KEY in environment.
    """

    def __init__(self, model: str = "gpt-4o-mini", api_key: str = "", base_url: str = "https://api.openai.com/v1"):
        import httpx
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=30.0)
        logger.info(f"Initialized OpenAILLMProvider with model '{model}' at {base_url}")

    async def generate_stream(self, messages: List[ChatMessage]) -> AsyncIterator[LLMChunk]:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
            "max_tokens": 256,
            "temperature": 0.7,
        }

        t0 = time.time()
        ttft_ms = None
        accumulated = ""

        async with self.client.stream("POST", url, json=payload, headers=headers) as response:
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    import json
                    data = json.loads(data_str)
                    delta = data["choices"][0]["delta"].get("content", "")
                    if delta:
                        if ttft_ms is None:
                            ttft_ms = round((time.time() - t0) * 1000, 1)
                            logger.info(f"LLM TTFT: {ttft_ms}ms")
                        accumulated += delta
                        yield LLMChunk(text=delta, is_final=False, total_text=accumulated, ttft_ms=ttft_ms or 0)
                except Exception:
                    continue

        total_ms = round((time.time() - t0) * 1000, 1)
        logger.info(f"LLM generation complete: '{accumulated[:60]}...' ({total_ms}ms)")
        yield LLMChunk(text="", is_final=True, total_text=accumulated, duration_ms=total_ms, ttft_ms=ttft_ms or 0)


_llm_provider_instance: Optional[LLMProvider] = None


def get_llm_provider() -> LLMProvider:
    """Factory providing singleton LLMProvider based on available API keys."""
    global _llm_provider_instance
    if _llm_provider_instance is None:
        if settings.GROQ_API_KEY:
            logger.info("Initializing Groq LLM Provider (llama-3.1-8b-instant)...")
            _llm_provider_instance = GroqLLMProvider(
                model="llama-3.1-8b-instant",
                api_key=settings.GROQ_API_KEY,
            )
        elif settings.OPENAI_API_KEY:
            logger.info("Initializing OpenAI LLM Provider (gpt-4o-mini)...")
            _llm_provider_instance = OpenAILLMProvider(
                model="gpt-4o-mini",
                api_key=settings.OPENAI_API_KEY,
            )
        else:
            logger.warning("No LLM API key found! LLM responses will be disabled until GROQ_API_KEY or OPENAI_API_KEY is set in .env")
            _llm_provider_instance = None
    return _llm_provider_instance
