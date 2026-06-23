"""Together AI provider."""
from __future__ import annotations

import time

from openai import OpenAI

from config.settings import settings
from src.llm.base import BaseLLMProvider, LLMResponse


class TogetherProvider(BaseLLMProvider):
    def __init__(self) -> None:
        self._client: OpenAI | None = None

    @property
    def provider_name(self) -> str:
        return "together"

    def is_available(self) -> bool:
        return bool(settings.together_api_key)

    def _get_client(self) -> OpenAI:
        if self._client is None:
            import httpx
            http_client = httpx.Client(timeout=httpx.Timeout(60.0, connect=15.0))
            self._client = OpenAI(
                api_key=settings.together_api_key,
                base_url="https://api.together.xyz/v1",
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
            model=settings.together_model,
            messages=messages,
            temperature=temperature if temperature is not None else settings.llm_temperature,
            max_tokens=max_tokens or settings.llm_max_tokens,
        )

        latency = (time.perf_counter() - t0) * 1000
        usage = resp.usage
        in_tok = usage.prompt_tokens if usage else 0
        out_tok = usage.completion_tokens if usage else 0
        cost = (in_tok / 1_000_000) * 0.18 + (out_tok / 1_000_000) * 0.18  # ~$0.18/M tok

        return LLMResponse(
            content=resp.choices[0].message.content or "",
            model=settings.together_model,
            provider="together",
            token_usage={"input": in_tok, "output": out_tok, "total": in_tok + out_tok},
            cost_usd=cost,
            latency_ms=latency,
        )

    async def agenerate(self, prompt: str, *, system: str = "", temperature: float | None = None,
                        max_tokens: int | None = None) -> LLMResponse:
        import asyncio
        return await asyncio.to_thread(self.generate, prompt, system=system,
                                       temperature=temperature, max_tokens=max_tokens)
