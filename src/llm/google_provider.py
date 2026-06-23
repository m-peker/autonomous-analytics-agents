"""Google Gemini provider."""
from __future__ import annotations

import time

import google.generativeai as genai

from config.settings import settings
from src.llm.base import BaseLLMProvider, LLMResponse

PRICING: dict[str, tuple[float, float]] = {
    "gemini-1.5-flash": (0.000075, 0.0003),
    "gemini-1.5-pro": (0.00125, 0.005),
}


class GoogleProvider(BaseLLMProvider):
    def __init__(self) -> None:
        self._configured = False

    @property
    def provider_name(self) -> str:
        return "google"

    def is_available(self) -> bool:
        return bool(settings.google_api_key)

    def _configure(self) -> None:
        if not self._configured and settings.google_api_key:
            genai.configure(api_key=settings.google_api_key)
            self._configured = True

    def generate(self, prompt: str, *, system: str = "", temperature: float | None = None,
                 max_tokens: int | None = None) -> LLMResponse:
        self._configure()
        t0 = time.perf_counter()

        model = genai.GenerativeModel(
            settings.google_model,
            system_instruction=system or None,
        )
        resp = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature if temperature is not None else settings.llm_temperature,
                max_output_tokens=max_tokens or settings.llm_max_tokens,
            ),
        )

        latency = (time.perf_counter() - t0) * 1000
        usage = resp.usage_metadata
        in_tok = usage.prompt_token_count if usage else 0
        out_tok = usage.candidates_token_count if usage else 0

        price_in, price_out = PRICING.get(settings.google_model, (0.000075, 0.0003))
        cost = (in_tok / 1000) * price_in + (out_tok / 1000) * price_out

        return LLMResponse(
            content=resp.text or "",
            model=settings.google_model,
            provider="google",
            token_usage={"input": in_tok, "output": out_tok, "total": in_tok + out_tok},
            cost_usd=cost,
            latency_ms=latency,
        )

    async def agenerate(self, prompt: str, *, system: str = "", temperature: float | None = None,
                        max_tokens: int | None = None) -> LLMResponse:
        import asyncio
        return await asyncio.to_thread(self.generate, prompt, system=system,
                                       temperature=temperature, max_tokens=max_tokens)
