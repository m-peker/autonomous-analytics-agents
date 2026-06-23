"""Tests for the LLM factory and multi-provider layer."""
from __future__ import annotations

import pytest

from config.settings import Settings


class TestSettings:
    def test_default_provider_is_openai(self):
        s = Settings()
        assert s.llm_provider == "openai"

    def test_model_for_provider(self):
        s = Settings(openai_model="gpt-4o-mini", anthropic_model="claude-3-haiku-20240307")
        assert s.model_for_provider("openai") == "gpt-4o-mini"
        assert s.model_for_provider("anthropic") == "claude-3-haiku-20240307"

    def test_supported_models_includes_ollama(self):
        s = Settings()
        assert any("ollama" in m for m in s.supported_models)


class TestLLMResponse:
    def test_response_dataclass(self):
        from src.llm.base import LLMResponse
        r = LLMResponse(content="Hello", model="gpt-4o-mini", provider="openai",
                        token_usage={"input": 10, "output": 5, "total": 15},
                        cost_usd=0.0001, latency_ms=250)
        assert r.content == "Hello"
        assert r.cost_usd == 0.0001
        assert r.token_usage["total"] == 15
