"""Offline checks for provider selection and the Claude client (the SDK call is faked)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from conftest import solver
from questionize.config import ProviderConfig, load_settings
from questionize.llm import AnthropicLLM, LLMError, OpenAICompatLLM, make_llm
from questionize.schemas import SolverResult

CLAUDE = ProviderConfig("anthropic", "", "sk-test", "claude-sonnet-5-5", effort="high")


def test_defaults_to_meta_muse_spark(monkeypatch):
    for var in ("LLM_PROVIDER", "SOLVER_PROVIDER", "META_MODEL", "SOLVER_MODEL"):
        monkeypatch.delenv(var, raising=False)
    s = load_settings()
    assert s.primary.name == "meta" and s.primary.model == "muse-spark-1.3"
    assert s.solver == s.primary


def test_claude_provider_defaults_to_sonnet(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    for var in ("SOLVER_PROVIDER", "ANTHROPIC_MODEL", "SOLVER_MODEL", "ANTHROPIC_EFFORT"):
        monkeypatch.delenv(var, raising=False)
    s = load_settings()
    assert s.primary.name == "anthropic" and s.primary.model == "claude-sonnet-5-5"
    assert s.primary.effort == "high"


def test_solver_model_override(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.delenv("SOLVER_PROVIDER", raising=False)
    monkeypatch.setenv("SOLVER_MODEL", "claude-haiku-5-5")
    s = load_settings()
    assert s.primary.model == "claude-sonnet-5-5"
    assert s.solver.name == "anthropic" and s.solver.model == "claude-haiku-5-5"


def test_blank_provider_vars_fall_back_to_defaults(monkeypatch):
    # .env.example ships SOLVER_PROVIDER= and SOLVER_MODEL= empty.
    monkeypatch.setenv("LLM_PROVIDER", "")
    monkeypatch.setenv("SOLVER_PROVIDER", "")
    monkeypatch.setenv("SOLVER_MODEL", "")
    s = load_settings()
    assert s.primary.name == "meta" and s.solver == s.primary


def test_make_llm_picks_client_by_provider():
    assert isinstance(make_llm(CLAUDE, timeout=5), AnthropicLLM)
    assert isinstance(make_llm(ProviderConfig("meta", "http://x", "k", "m"), timeout=5), OpenAICompatLLM)


def test_missing_anthropic_key_is_reported():
    with pytest.raises(LLMError, match="ANTHROPIC_API_KEY"):
        AnthropicLLM(ProviderConfig("anthropic", "", "", "claude-sonnet-5-5"))


class FakeMessages:
    def __init__(self, response):
        self.response = response
        self.calls: list[dict] = []

    async def parse(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def fake_llm(response) -> tuple[AnthropicLLM, FakeMessages]:
    llm = AnthropicLLM(CLAUDE)
    messages = FakeMessages(response)
    llm._client = SimpleNamespace(beta=SimpleNamespace(messages=messages))
    return llm, messages


async def test_claude_returns_parsed_output_without_sampling_params():
    llm, messages = fake_llm(SimpleNamespace(stop_reason="end_turn", stop_details=None, parsed_output=solver("C")))
    out = await llm.complete("sys", "user", SolverResult, temperature=0.0)

    assert out.answer_label == "C"
    call = messages.calls[0]
    assert call["model"] == "claude-sonnet-5-5"
    assert call["output_format"] is SolverResult
    assert call["output_config"] == {"effort": "high"}
    assert "temperature" not in call


async def test_claude_refusal_raises():
    refusal = SimpleNamespace(stop_reason="refusal", stop_details=SimpleNamespace(category="general_harms"), parsed_output=None)
    llm, _ = fake_llm(refusal)
    with pytest.raises(LLMError, match="general_harms"):
        await llm.complete("sys", "user", SolverResult)


async def test_claude_truncated_output_raises():
    llm, _ = fake_llm(SimpleNamespace(stop_reason="max_tokens", stop_details=None, parsed_output=None))
    with pytest.raises(LLMError, match="output tokens"):
        await llm.complete("sys", "user", SolverResult)


def test_padded_keys_are_forgiven():
    from questionize.import_scan import PageStructure
    from questionize.llm import parse_structured

    options = ", ".join(f'{{"label ": "{label}", "text": "Option {label}."}}' for label in "ABCDE")
    reply = '{"kind": "question", "passage": "P.", "stem": "S?", "options ": [' + options + '], "answer_key ": "E", "continues_on_next_page ": false}'
    page = parse_structured(reply, PageStructure)
    assert page.answer_key == "E" and [o.label for o in page.options] == list("ABCDE")
    # Truly broken JSON still fails as a validation error, so the caller's retry loop handles it.
    import pydantic
    import pytest

    with pytest.raises(pydantic.ValidationError):
        parse_structured('{"kind": "question", "options [{" : "A"', PageStructure)
