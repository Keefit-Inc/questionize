"""Runtime configuration, read from environment variables (see .env.example)."""

from __future__ import annotations

import os
from dataclasses import dataclass, replace

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    base_url: str
    api_key: str
    model: str
    # Claude only: output_config.effort (low | medium | high | xhigh | max).
    effort: str = ""


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
    if name == "anthropic":
        # Alternative provider for development; same pipeline, different client.
        return ProviderConfig(
            name="anthropic",
            base_url="",
            api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5"),
            effort=os.getenv("ANTHROPIC_EFFORT", "high"),
        )
    raise ValueError(f"Unknown LLM provider: {name!r} (expected 'meta', 'baseten' or 'anthropic')")


@dataclass(frozen=True)
class Settings:
    # Provider used by the analyst, writer and critic agents.
    primary: ProviderConfig
    # Provider used by the blind solver. Pointing it at a different model
    # (e.g. Muse Spark Open on Baseten) gives cross-model verification.
    solver: ProviderConfig
    # Shared secret Rails sends as X-Internal-Token. Empty means every /v1 request is refused.
    internal_token: str = ""
    max_revisions: int = 2
    timeout_seconds: float = 300.0
    max_article_chars: int = 40_000
    # Passages copying a longer run of consecutive article words go back for a rewrite.
    max_copied_words: int = 12
    # Argument Judge: samples per judge model, and the gate an item must clear.
    judge_enabled: bool = True
    judge_samples: int = 3
    judge_min_first_rate: float = 0.9
    judge_min_margin: float = 0.15


def load_settings() -> Settings:
    # Blank values (as copied from .env.example) mean "use the default".
    primary_name = os.getenv("LLM_PROVIDER", "").strip() or "meta"
    solver_name = os.getenv("SOLVER_PROVIDER", "").strip() or primary_name
    solver = _provider(solver_name)
    if solver_model := os.getenv("SOLVER_MODEL", "").strip():
        solver = replace(solver, model=solver_model)
    return Settings(
        primary=_provider(primary_name),
        solver=solver,
        internal_token=os.getenv("INTERNAL_TOKEN", ""),
        max_revisions=int(os.getenv("MAX_REVISIONS", "2")),
        timeout_seconds=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "300")),
        max_article_chars=int(os.getenv("MAX_ARTICLE_CHARS", "40000")),
        max_copied_words=int(os.getenv("MAX_COPIED_WORDS", "12")),
        judge_enabled=os.getenv("JUDGE_ENABLED", "true").strip().lower() not in ("0", "false", "no"),
        judge_samples=int(os.getenv("JUDGE_SAMPLES", "3")),
        judge_min_first_rate=float(os.getenv("JUDGE_MIN_FIRST_RATE", "0.9")),
        judge_min_margin=float(os.getenv("JUDGE_MIN_MARGIN", "0.15")),
    )
