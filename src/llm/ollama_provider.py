"""Ollama provider for local models."""
from __future__ import annotations

import time

import httpx

from config.settings import settings
from src.llm.base import BaseLLMProvider, LLMResponse


class OllamaProvider(BaseLLMProvider):
    def __init__(self) -> None:
        self._base = settings.ollama_base_url.rstrip("/")

    @property
    def provider_name(self) -> str:
        return "ollama"

    def is_available(self) -> bool:
        try:
            resp = httpx.get(f"{self._base}/api/tags", timeout=3)
            return resp.is_success
        except Exception:
            return False

    def generate(self, prompt: str, *, system: str = "", temperature: float | None = None,
                 max_tokens: int | None = None) -> LLMResponse:
        t0 = time.perf_counter()

        payload: dict = {
            "model": settings.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature if temperature is not None else settings.llm_temperature,
                "num_predict": max_tokens or settings.llm_max_tokens,
            },
        }
        if system:
            payload["system"] = system

        resp = httpx.post(f"{self._base}/api/generate", json=payload, timeout=300)
        resp.raise_for_status()
        data = resp.json()

        latency = (time.perf_counter() - t0) * 1000
        eval_count = data.get("eval_count", 0)
        prompt_eval = data.get("prompt_eval_count", 0)

        return LLMResponse(
            content=data.get("response", ""),
            model=settings.ollama_model,
            provider="ollama",
            token_usage={"input": prompt_eval, "output": eval_count, "total": prompt_eval + eval_count},
            cost_usd=0.0,
            latency_ms=latency,
        )

    async def agenerate(self, prompt: str, *, system: str = "", temperature: float | None = None,
                        max_tokens: int | None = None) -> LLMResponse:
        import asyncio
        return await asyncio.to_thread(self.generate, prompt, system=system,
                                       temperature=temperature, max_tokens=max_tokens)
