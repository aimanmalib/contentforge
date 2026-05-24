"""MiMo V2.5 Pro API client with streaming, retries, and token tracking."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional

import httpx

from .config import MiMoConfig

logger = logging.getLogger(__name__)


@dataclass
class TokenUsage:
    """Track token consumption per call and cumulative."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0

    def add(self, other: "TokenUsage") -> None:
        self.prompt_tokens += other.prompt_tokens
        self.completion_tokens += other.completion_tokens
        self.total_tokens += other.total_tokens
        self.cached_tokens += other.cached_tokens


@dataclass
class ChatMessage:
    role: str
    content: str
    reasoning_content: Optional[str] = None


@dataclass
class ChatResponse:
    content: str
    reasoning_content: Optional[str] = None
    usage: TokenUsage = field(default_factory=TokenUsage)
    model: str = ""
    finish_reason: str = ""
    latency_ms: float = 0.0


@dataclass
class StreamChunk:
    delta: str
    reasoning_delta: Optional[str] = None
    finish_reason: Optional[str] = None
    usage: Optional[TokenUsage] = None


class MiMoClient:
    """Async client for Xiaomi MiMo V2.5 Pro Token Plan API.

    Uses api-key header (NOT Authorization: Bearer) per MiMo Token Plan spec.
    Endpoint: https://token-plan-sgp.xiaomimimo.com/v1/chat/completions
    """

    def __init__(self, config: MiMoConfig):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
        self.total_usage = TokenUsage()
        self._call_count = 0
        self._total_latency_ms = 0.0

    async def __aenter__(self) -> "MiMoClient":
        self._client = httpx.AsyncClient(
            base_url=self.config.base_url,
            headers=self.config.headers,
            timeout=httpx.Timeout(self.config.timeout),
        )
        return self

    async def __aexit__(self, *args) -> None:
        if self._client:
            await self._client.aclose()

    @property
    def avg_latency_ms(self) -> float:
        if self._call_count == 0:
            return 0.0
        return self._total_latency_ms / self._call_count

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> ChatResponse:
        """Send a chat completion request to MiMo API."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use async with.")

        payload = {
            "model": model or self.config.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "max_tokens": max_tokens or self.config.max_tokens,
            "temperature": temperature or self.config.temperature,
            "top_p": self.config.top_p,
            "stream": stream,
        }

        start = time.monotonic()

        for attempt in range(self.config.max_retries):
            try:
                if stream:
                    return await self._stream_chat(payload)
                else:
                    resp = await self._client.post("/chat/completions", json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    break
            except (httpx.HTTPStatusError, httpx.ConnectError) as e:
                logger.warning(f"MiMo API attempt {attempt+1} failed: {e}")
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
                else:
                    raise

        latency = (time.monotonic() - start) * 1000
        self._call_count += 1
        self._total_latency_ms += latency

        choice = data["choices"][0]
        usage_data = data.get("usage", {})

        usage = TokenUsage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
            cached_tokens=usage_data.get("prompt_tokens_details", {}).get("cached_tokens", 0),
        )
        self.total_usage.add(usage)

        msg = choice.get("message", {})

        return ChatResponse(
            content=msg.get("content", ""),
            reasoning_content=msg.get("reasoning_content"),
            usage=usage,
            model=data.get("model", ""),
            finish_reason=choice.get("finish_reason", ""),
            latency_ms=latency,
        )

    async def _stream_chat(self, payload: dict) -> ChatResponse:
        """Handle streaming SSE response from MiMo."""
        payload["stream"] = True
        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        usage = TokenUsage()

        async with self._client.stream(
            "POST", "/chat/completions", json=payload
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                line_data = line[6:].strip()
                if line_data == "[DONE]":
                    break
                try:
                    chunk = json.loads(line_data)
                    delta = chunk["choices"][0].get("delta", {})
                    if "content" in delta and delta["content"]:
                        content_parts.append(delta["content"])
                    if "reasoning_content" in delta and delta["reasoning_content"]:
                        reasoning_parts.append(delta["reasoning_content"])
                    if "usage" in chunk:
                        usage = TokenUsage(
                            prompt_tokens=chunk["usage"].get("prompt_tokens", 0),
                            completion_tokens=chunk["usage"].get("completion_tokens", 0),
                            total_tokens=chunk["usage"].get("total_tokens", 0),
                        )
                except (json.JSONDecodeError, KeyError):
                    continue

        self.total_usage.add(usage)

        return ChatResponse(
            content="".join(content_parts),
            reasoning_content="".join(reasoning_parts) if reasoning_parts else None,
            usage=usage,
            model=payload.get("model", ""),
            finish_reason="stop",
        )

    async def stream_chunks(
        self,
        messages: list[ChatMessage],
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[StreamChunk]:
        """Yield streaming chunks for real-time display."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use async with.")

        payload = {
            "model": model or self.config.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "max_tokens": max_tokens or self.config.max_tokens,
            "temperature": temperature or self.config.temperature,
            "top_p": self.config.top_p,
            "stream": True,
        }

        async with self._client.stream(
            "POST", "/chat/completions", json=payload
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                line_data = line[6:].strip()
                if line_data == "[DONE]":
                    break
                try:
                    chunk = json.loads(line_data)
                    delta = chunk["choices"][0].get("delta", {})
                    finish = chunk["choices"][0].get("finish_reason")
                    usage_data = chunk.get("usage")

                    yield StreamChunk(
                        delta=delta.get("content", "") or "",
                        reasoning_delta=delta.get("reasoning_content"),
                        finish_reason=finish,
                        usage=TokenUsage(**usage_data) if usage_data else None,
                    )
                except (json.JSONDecodeError, KeyError):
                    continue
