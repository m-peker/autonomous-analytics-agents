"""LLM provider factory with automatic fallback and cost tracking.

Priority: primary provider → fallback list → Ollama (local, always last resort).

All LLM calls from agents flow through this module so cost & latency are
tracked centrally.  The `CostTracker` singleton exposes a running total that
the Streamlit dashboard can display in real-time.
"""
from __future__ import annotations

import logging
import threading
from typing import Any

from config.settings import ProviderKind, settings
from src.llm.base import BaseLLMProvider, LLMResponse

logger = logging.getLogger(__name__)

# ── Lazy imports to avoid pulling in every SDK at startup ────────────────────

_PROVIDER_CLASSES: dict[ProviderKind, str] = {
    "openai": "src.llm.openai_provider.OpenAIProvider",
    "anthropic": "src.llm.anthropic_provider.AnthropicProvider",
    "groq": "src.llm.groq_provider.GroqProvider",
    "together": "src.llm.together_provider.TogetherProvider",
    "google": "src.llm.google_provider.GoogleProvider",
    "ollama": "src.llm.ollama_provider.OllamaProvider",
}


def _import_provider(kind: ProviderKind) -> BaseLLMProvider | None:
    path = _PROVIDER_CLASSES.get(kind)
    if not path:
        return None
    mod_path, cls_name = path.rsplit(".", 1)
    import importlib
    try:
        mod = importlib.import_module(mod_path)
        return getattr(mod, cls_name)()
    except Exception as exc:
        logger.warning("Cannot load %s provider: %s", kind, exc)
        return None


# ── Cost tracker ─────────────────────────────────────────────────────────────

class CostTracker:
    """Thread-safe running tally of API spend."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.total_usd = 0.0
        self.calls: list[dict[str, Any]] = []

    def record(self, resp: LLMResponse) -> None:
        with self._lock:
            self.total_usd += resp.cost_usd
            self.calls.append({
                "provider": resp.provider,
                "model": resp.model,
                "tokens": resp.token_usage.get("total", 0),
                "cost": resp.cost_usd,
                "latency_ms": resp.latency_ms,
            })

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total_cost_usd": round(self.total_usd, 6),
                "call_count": len(self.calls),
                "last_calls": self.calls[-20:],
            }


cost_tracker = CostTracker()


# ── Factory ──────────────────────────────────────────────────────────────────

class LLMFactory:
    """Returns a working provider with automatic fallback."""

    def __init__(self) -> None:
        self._providers: dict[ProviderKind, BaseLLMProvider | None] = {}

    def _get_or_load(self, kind: ProviderKind) -> BaseLLMProvider | None:
        if kind not in self._providers:
            self._providers[kind] = _import_provider(kind)
        return self._providers[kind]

    def get_provider(self, preferred: ProviderKind | None = None) -> BaseLLMProvider:
        """Return the first available provider in the priority chain.

        Chain: preferred → settings.llm_provider → fallback list → ollama.
        """
        chain: list[ProviderKind] = []
        if preferred:
            chain.append(preferred)
        chain.append(settings.llm_provider)
        chain.extend(settings.fallback_providers)
        if "ollama" not in chain:
            chain.append("ollama")

        for kind in chain:
            provider = self._get_or_load(kind)
            if provider and provider.is_available():
                logger.info("LLM → %s (%s)", kind, provider.provider_name)
                return provider

        raise RuntimeError(
            "No LLM provider is available. Set at least one API key "
            "(OPENAI_API_KEY, ANTHROPIC_API_KEY, GROQ_API_KEY, etc.) "
            "or ensure Ollama is running at " + settings.ollama_base_url
        )

    def generate(self, prompt: str, *, system: str = "",
                 provider: ProviderKind | None = None,
                 temperature: float | None = None,
                 max_tokens: int | None = None) -> LLMResponse:
        p = self.get_provider(provider)
        resp = p.generate(prompt, system=system, temperature=temperature, max_tokens=max_tokens)
        if settings.track_costs:
            cost_tracker.record(resp)
        return resp

    async def agenerate(self, prompt: str, *, system: str = "",
                        provider: ProviderKind | None = None,
                        temperature: float | None = None,
                        max_tokens: int | None = None) -> LLMResponse:
        p = self.get_provider(provider)
        resp = await p.agenerate(prompt, system=system, temperature=temperature, max_tokens=max_tokens)
        if settings.track_costs:
            cost_tracker.record(resp)
        return resp


# Global singleton — agents import this
llm = LLMFactory()
