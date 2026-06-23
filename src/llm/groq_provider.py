"""Groq provider — fastest inference via LPU."""
from __future__ import annotations

import time

import httpx
from groq import Groq

from config.settings import settings
from src.llm.base import BaseLLMProvider, LLMResponse

PRICING: dict[str, tuple[float, float]] = {
    "llama-3.1-8b-instant": (0.00005, 0.00008),
    "mixtral-8x7b-32768": (0.00024, 0.00024),
}


class GroqProvider(BaseLLMProvider):
    def __init__(self) -> None:
        self._client: Groq | None = None

    @property
    def provider_name(self) -> str:
        return "groq"

    def is_available(self) -> bool:
        return bool(settings.groq_api_key)

    def _get_client(self) -> Groq:
        if self._client is None:
            self._client = Groq(
                api_key=settings.groq_api_key,
                http_client=httpx.Client(timeout=httpx.Timeout(60.0, connect=15.0)),
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
            model=settings.groq_model,
            messages=messages,
            temperature=temperature if temperature is not None else settings.llm_temperature,
            max_tokens=max_tokens or settings.llm_max_tokens,
        )

        latency = (time.perf_counter() - t0) * 1000
        usage = resp.usage
        in_tok = usage.prompt_tokens if usage else 0
        out_tok = usage.completion_tokens if usage else 0

        price_in, price_out = PRICING.get(settings.groq_model, (0.00005, 0.00008))
        cost = (in_tok / 1000) * price_in + (out_tok / 1000) * price_out

        return LLMResponse(
            content=resp.choices[0].message.content or "",
            model=settings.groq_model,
            provider="groq",
            token_usage={"input": in_tok, "output": out_tok, "total": in_tok + out_tok},
            cost_usd=cost,
            latency_ms=latency,
        )

    async def agenerate(self, prompt: str, *, system: str = "", temperature: float | None = None,
                        max_tokens: int | None = None) -> LLMResponse:
        import asyncio
        return await asyncio.to_thread(self.generate, prompt, system=system,
                                       temperature=temperature, max_tokens=max_tokens)
