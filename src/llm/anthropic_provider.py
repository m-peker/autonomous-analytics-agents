"""Anthropic provider (Claude 3 Haiku / Sonnet)."""
from __future__ import annotations

import time

from anthropic import Anthropic

from config.settings import settings
from src.llm.base import BaseLLMProvider, LLMResponse

PRICING: dict[str, tuple[float, float]] = {
    "claude-3-haiku-20240307": (0.00025, 0.00125),
    "claude-3-5-sonnet-20240620": (0.003, 0.015),
}


class AnthropicProvider(BaseLLMProvider):
    def __init__(self) -> None:
        self._client: Anthropic | None = None

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def is_available(self) -> bool:
        return bool(settings.anthropic_api_key)

    def _get_client(self) -> Anthropic:
        if self._client is None:
            self._client = Anthropic(api_key=settings.anthropic_api_key)
        return self._client

    def generate(self, prompt: str, *, system: str = "", temperature: float | None = None,
                 max_tokens: int | None = None) -> LLMResponse:
        client = self._get_client()
        t0 = time.perf_counter()

        kwargs: dict = {
            "model": settings.anthropic_model,
            "max_tokens": max_tokens or settings.llm_max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        kwargs["temperature"] = temperature if temperature is not None else settings.llm_temperature

        resp = client.messages.create(**kwargs)  # type: ignore[arg-type]

        latency = (time.perf_counter() - t0) * 1000
        usage = resp.usage
        in_tok = usage.input_tokens if usage else 0
        out_tok = usage.output_tokens if usage else 0

        price_in, price_out = PRICING.get(settings.anthropic_model, (0.00025, 0.00125))
        cost = (in_tok / 1000) * price_in + (out_tok / 1000) * price_out

        content = resp.content[0].text if isinstance(resp.content, list) else str(resp.content)

        return LLMResponse(
            content=content,
            model=settings.anthropic_model,
            provider="anthropic",
            token_usage={"input": in_tok, "output": out_tok, "total": in_tok + out_tok},
            cost_usd=cost,
            latency_ms=latency,
        )

    async def agenerate(self, prompt: str, *, system: str = "", temperature: float | None = None,
                        max_tokens: int | None = None) -> LLMResponse:
        import asyncio
        return await asyncio.to_thread(self.generate, prompt, system=system,
                                       temperature=temperature, max_tokens=max_tokens)
