"""Abstract base for all LLM providers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    token_usage: dict[str, int] = field(default_factory=dict)
    cost_usd: float = 0.0
    latency_ms: float = 0.0


class BaseLLMProvider(ABC):
    """Every provider implements this interface."""

    @abstractmethod
    def generate(self, prompt: str, *, system: str = "", temperature: float | None = None,
                 max_tokens: int | None = None) -> LLMResponse:
        ...

    @abstractmethod
    async def agenerate(self, prompt: str, *, system: str = "", temperature: float | None = None,
                        max_tokens: int | None = None) -> LLMResponse:
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is configured and reachable."""
        ...
