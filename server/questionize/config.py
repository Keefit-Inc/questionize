"""Runtime configuration, read from environment variables (see .env.example)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    base_url: str
    api_key: str
    model: str


def _provider(name: str) -> ProviderConfig:
    name = name.strip().lower()
    if name == "meta":
        return ProviderConfig(
            name="meta",
            base_url=os.getenv("META_BASE_URL", "https://api.meta.ai/v1"),
            api_key=os.getenv("MODEL_API_KEY", ""),
            model=os.getenv("META_MODEL", "muse-spark-1.3"),
        )
    if name == "baseten":
        return ProviderConfig(
            name="baseten",
            base_url=os.getenv("BASETEN_BASE_URL", "https://inference.baseten.co/v1"),
            api_key=os.getenv("BASETEN_API_KEY", ""),
            model=os.getenv("BASETEN_MODEL", "meta-models/muse-spark-open-1026"),
        )
    raise ValueError(f"Unknown LLM provider: {name!r} (expected 'meta' or 'baseten')")


@dataclass(frozen=True)
class Settings:
    # Provider used by the analyst, writer and critic agents.
    primary: ProviderConfig
    # Provider used by the blind solver. Pointing it at a different model
    # (e.g. Muse Spark Open on Baseten) gives cross-model verification.
    solver: ProviderConfig
    max_revisions: int = 2
    timeout_seconds: float = 120.0
    max_article_chars: int = 40_000
    allowed_origins: list[str] = field(default_factory=lambda: ["*"])


def load_settings() -> Settings:
    primary_name = os.getenv("LLM_PROVIDER", "meta")
    solver_name = os.getenv("SOLVER_PROVIDER", primary_name)
    origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
    return Settings(
        primary=_provider(primary_name),
        solver=_provider(solver_name),
        max_revisions=int(os.getenv("MAX_REVISIONS", "2")),
        timeout_seconds=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "120")),
        max_article_chars=int(os.getenv("MAX_ARTICLE_CHARS", "40000")),
        allowed_origins=origins or ["*"],
    )
