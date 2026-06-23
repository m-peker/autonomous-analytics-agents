"""Central configuration via pydantic-settings.

Supports: OpenAI, Anthropic, Groq, Together AI, Google Gemini, and Ollama (local).
Sensitive keys loaded from environment variables (primary) or Google Secret Manager (fallback).

Local development:
    - Set OPENAI_API_KEY, etc. in .env file or system environment

GCP deployment (Cloud Run) — RECOMMENDED APPROACH:
    - Pass API keys directly via --set-env-vars during gcloud run deploy
    - Example: --set-env-vars=\"OPENAI_API_KEY=sk-...\"
    - Set GCP_PROJECT and GCS_BUCKET_NAME env vars
    - Optional: Use --clear-secrets to remove any old Secret Manager bindings

GCP deployment (Legacy fallback):
    - Secret Manager auto-loads keys if env vars are empty (fallback only)
    - To use: Store secrets in Secret Manager first
    - Deploy with --set-secrets=\"OPENAI_API_KEY=OPENAI_API_KEY:latest\"
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ProviderKind = Literal["openai", "anthropic", "groq", "together", "google", "ollama"]


def _load_secret(secret_name: str) -> str:
    """Try to load a secret from Google Secret Manager.

    Falls back silently to env var if not on GCP or secret not found.
    """
    try:
        from google.cloud import secretmanager
        project = os.getenv("GCP_PROJECT", os.getenv("GOOGLE_CLOUD_PROJECT", ""))
        if not project:
            return ""
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project}/secrets/{secret_name}/versions/latest"
        resp = client.access_secret_version(request={"name": name})
        return resp.payload.data.decode("utf-8")
    except Exception:
        return ""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── GCP deployment ────────────────────────────────────────────────────
    gcp_project: str = ""
    gcs_bucket_name: str = ""
    cloud_run_service: str = "analytics-agents"
    cloud_run_region: str = "us-central1"

    # ── Project paths (local fallback) ─────────────────────────────────────
    project_root: Path = Path(__file__).resolve().parents[1]
    upload_dir: Path = Field(default=Path("./data/uploads"))
    output_dir: Path = Field(default=Path("./data/outputs"))
    chroma_persist_dir: Path = Field(default=Path("./data/chroma"))
    sqlite_path: Path = Field(default=Path("./data/platform.db"))

    # ── LLM provider selection ─────────────────────────────────────────────
    llm_provider: ProviderKind = "openai"
    fallback_providers: list[ProviderKind] = ["groq", "together", "anthropic"]
    llm_temperature: float = 0.3
    llm_max_tokens: int = 4096

    # ── OpenAI ─────────────────────────────────────────────────────────────
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # ── Anthropic ──────────────────────────────────────────────────────────
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-haiku-20240307"

    # ── Groq (fast inference) ──────────────────────────────────────────────
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"

    # ── Together AI ────────────────────────────────────────────────────────
    together_api_key: str = ""
    together_model: str = "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"

    # ── Google Gemini ──────────────────────────────────────────────────────
    google_api_key: str = ""
    google_model: str = "gemini-1.5-flash"

    # ── Ollama (local, no key needed) ──────────────────────────────────────
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3"

    # ── Web scraping ───────────────────────────────────────────────────────
    firecrawl_api_key: str = ""
    tavily_api_key: str = ""

    # ── RAG ────────────────────────────────────────────────────────────────
    chunk_size: int = 1000
    chunk_overlap: int = 200
    embedding_model: str = "text-embedding-3-small"
    top_k_retrieval: int = 5

    # ── Budget guardrails ──────────────────────────────────────────────────
    max_daily_spend_usd: float = 5.0
    track_costs: bool = True

    # ── GCP Secret Manager auto-load ──────────────────────────────────────
    # Called after env vars are loaded; fetches from Secret Manager if on GCP.
    @model_validator(mode="after")
    def _load_gcp_secrets(self) -> "Settings":
        """Load API keys from GCP Secret Manager when running on Cloud Run."""
        if not self.gcp_project:
            return self

        secret_map = {
            "OPENAI_API_KEY": "openai_api_key",
            "ANTHROPIC_API_KEY": "anthropic_api_key",
            "GROQ_API_KEY": "groq_api_key",
            "TOGETHER_API_KEY": "together_api_key",
            "GOOGLE_API_KEY": "google_api_key",
            "FIRECRAWL_API_KEY": "firecrawl_api_key",
            "TAVILY_API_KEY": "tavily_api_key",
        }

        for secret_id, attr in secret_map.items():
            current = getattr(self, attr, "")
            if not current:
                val = _load_secret(secret_id)
                if val:
                    object.__setattr__(self, attr, val)

        return self

    @property
    def supported_models(self) -> list[str]:
        models = []
        if self.openai_api_key:
            models.append("gpt-4o-mini")
            models.append("gpt-4o")
        if self.anthropic_api_key:
            models.append("claude-3-haiku")
            models.append("claude-3.5-sonnet")
        if self.groq_api_key:
            models.append("groq-llama3")
        if self.together_api_key:
            models.append("together-llama3")
        if self.google_api_key:
            models.append("gemini-1.5-flash")
        models.append("ollama-qwen3")
        return models or ["ollama-qwen3"]

    def model_for_provider(self, provider: ProviderKind) -> str:
        mapping = {
            "openai": self.openai_model,
            "anthropic": self.anthropic_model,
            "groq": self.groq_model,
            "together": self.together_model,
            "google": self.google_model,
            "ollama": self.ollama_model,
        }
        return mapping[provider]


settings = Settings()
