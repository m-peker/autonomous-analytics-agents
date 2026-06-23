"""OpenAI provider (GPT-4o-mini, GPT-4o)."""
from __future__ import annotations

import logging
import time

import httpx
from openai import OpenAI

from config.settings import settings
from src.llm.base import BaseLLMProvider, LLMResponse

logger = logging.getLogger(__name__)

# Approximate pricing per 1K tokens (input / output)
PRICING: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.00015, 0.0006),
    "gpt-4o": (0.0025, 0.01),
    "gpt-4o-2024-08-06": (0.0025, 0.01),
}


class OpenAIProvider(BaseLLMProvider):
    def __init__(self) -> None:
        self._client: OpenAI | None = None

    @property
    def provider_name(self) -> str:
        return "openai"

    def is_available(self) -> bool:
        return bool(settings.openai_api_key)

    def _get_client(self) -> OpenAI:
        if self._client is None:
            http_client = httpx.Client(
                timeout=httpx.Timeout(60.0, connect=15.0),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            )
            self._client = OpenAI(
                api_key=settings.openai_api_key,
                http_client=http_client,
                max_retries=2,
            )
        return self._client

    def generate(self, prompt: str, *, system: str = "", temperature: float | None = None,
                 max_tokens: int | None = None) -> LLMResponse:
        client = self._get_client()
        t0 = time.perf_counter()

        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        resp = client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            temperature=temperature if temperature is not None else settings.llm_temperature,
            max_tokens=max_tokens or settings.llm_max_tokens,
        )

        latency = (time.perf_counter() - t0) * 1000
        usage = resp.usage
        in_tok = usage.prompt_tokens if usage else 0
        out_tok = usage.completion_tokens if usage else 0

        price_in, price_out = PRICING.get(settings.openai_model, (0.00015, 0.0006))
        cost = (in_tok / 1000) * price_in + (out_tok / 1000) * price_out

        return LLMResponse(
            content=resp.choices[0].message.content or "",
            model=settings.openai_model,
            provider="openai",
            token_usage={"input": in_tok, "output": out_tok, "total": in_tok + out_tok},
            cost_usd=cost,
            latency_ms=latency,
        )

    async def agenerate(self, prompt: str, *, system: str = "", temperature: float | None = None,
                        max_tokens: int | None = None) -> LLMResponse:
        import asyncio
        return await asyncio.to_thread(self.generate, prompt, system=system,
                                       temperature=temperature, max_tokens=max_tokens)
