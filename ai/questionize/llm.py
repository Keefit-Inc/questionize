"""Structured-output LLM clients.

Both the Meta Model API and Baseten expose the OpenAI Chat Completions
protocol, so one client covers Muse Spark (hosted) and Muse Spark Open.
Claude runs through the Anthropic SDK as a stand-in provider.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Protocol, TypeVar

import anthropic
import openai
from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from .config import ProviderConfig

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    pass


class StructuredLLM(Protocol):
    model: str

    async def complete(
        self, system: str, user: str, schema: type[T], *, temperature: float = 0.4, images: list[str] | None = None
    ) -> T: ...


def _split_data_url(url: str) -> tuple[str, str]:
    """("image/png", base64 data) from a data: URL."""
    header, _, data = url.partition(",")
    media_type = header.removeprefix("data:").split(";")[0] or "image/jpeg"
    return media_type, data


def _extract_json(text: str) -> str:
    """Pull a JSON object out of a reply that may wrap it in prose or fences."""
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    if fenced:
        return fenced.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        return text[start : end + 1]
    return text


class OpenAICompatLLM:
    def __init__(self, provider: ProviderConfig, timeout: float = 120.0, max_retries: int = 4):
        if not provider.api_key:
            raise LLMError(
                f"No API key for provider '{provider.name}'. Set it in ai/.env (see .env.example)."
            )
        self.model = provider.model
        self.provider = provider.name
        self._client = AsyncOpenAI(base_url=provider.base_url, api_key=provider.api_key, timeout=timeout)
        self._max_retries = max_retries
        # Flipped off the first time the endpoint rejects json_schema.
        self._schema_mode = True
        self._send_temperature = True

    def _response_format(self, schema: type[BaseModel]) -> dict:
        if self._schema_mode:
            return {
                "type": "json_schema",
                "json_schema": {"name": schema.__name__, "schema": schema.model_json_schema()},
            }
        return {"type": "json_object"}

    async def complete(
        self, system: str, user: str, schema: type[T], *, temperature: float = 0.4, images: list[str] | None = None
    ) -> T:
        schema_hint = json.dumps(schema.model_json_schema())
        # Images (data: URLs) ride along as OpenAI-style content parts; they are never stored.
        user_content: str | list[dict] = (
            [{"type": "text", "text": user}] + [{"type": "image_url", "image_url": {"url": url}} for url in images]
            if images
            else user
        )
        messages = [
            {
                "role": "system",
                "content": f"{system}\n\nRespond with a single JSON object matching this JSON Schema:\n{schema_hint}",
            },
            {"role": "user", "content": user_content},
        ]
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            kwargs: dict = {"response_format": self._response_format(schema)}
            if self._send_temperature:
                kwargs["temperature"] = temperature
            try:
                resp = await self._client.chat.completions.create(model=self.model, messages=messages, **kwargs)
            except openai.BadRequestError as e:
                msg = str(e).lower()
                if self._send_temperature and "temperature" in msg:
                    # Some reasoning models fix sampling; retry without it.
                    log.warning("%s rejected temperature; omitting it", self.provider)
                    self._send_temperature = False
                    last_error = e
                    continue
                if self._schema_mode and ("response_format" in msg or "json_schema" in msg):
                    log.warning("%s rejected json_schema; falling back to json_object", self.provider)
                    self._schema_mode = False
                    last_error = e
                    continue
                raise LLMError(f"{self.provider} rejected the request: {e}") from e
            except (openai.APIConnectionError, openai.APITimeoutError, openai.RateLimitError) as e:
                last_error = e
                log.warning("%s transient error (attempt %d): %s", self.provider, attempt + 1, e)
                continue
            except openai.APIStatusError as e:
                raise LLMError(f"{self.provider} error {e.status_code}: {e}") from e

            content = resp.choices[0].message.content or ""
            try:
                return schema.model_validate_json(_extract_json(content))
            except ValidationError as e:
                last_error = e
                log.warning("%s returned invalid %s (attempt %d)", self.provider, schema.__name__, attempt + 1)
                messages = messages + [
                    {"role": "assistant", "content": content},
                    {"role": "user", "content": f"That JSON did not match the schema: {e}. Return corrected JSON only."},
                ]
        raise LLMError(f"{self.provider} failed to return valid {schema.__name__}: {last_error}")


class AnthropicLLM:
    """Claude through the Anthropic SDK, with the reply constrained to the schema."""

    # Re-runs a classifier-declined request on a fallback model inside the same call.
    _FALLBACK_BETA = "server-side-fallback-2026-07-01"

    def __init__(self, provider: ProviderConfig, timeout: float = 300.0, max_retries: int = 4):
        if not provider.api_key:
            raise LLMError("No API key for provider 'anthropic'. Set ANTHROPIC_API_KEY in ai/.env (see .env.example).")
        self.model = provider.model
        self.provider = provider.name
        self._effort = provider.effort
        # The SDK retries connection errors, 429 and 5xx itself.
        self._client = anthropic.AsyncAnthropic(api_key=provider.api_key, timeout=timeout, max_retries=max_retries)
        self._max_retries = max_retries

    async def complete(
        self, system: str, user: str, schema: type[T], *, temperature: float = 0.4, images: list[str] | None = None
    ) -> T:
        # Current Claude models fix sampling, so `temperature` is accepted for interface parity and not sent.
        content: str | list[dict] = user
        if images:
            content = [
                {"type": "image", "source": {"type": "base64", "media_type": m, "data": d}}
                for m, d in map(_split_data_url, images)
            ] + [{"type": "text", "text": user}]
        messages: list[dict] = [{"role": "user", "content": content}]
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                resp = await self._client.beta.messages.parse(
                    model=self.model,
                    max_tokens=16000,
                    system=system,
                    messages=messages,
                    output_format=schema,
                    output_config={"effort": self._effort} if self._effort else anthropic.omit,
                    betas=[self._FALLBACK_BETA],
                    fallbacks="default",
                )
            except anthropic.BadRequestError as e:
                raise LLMError(f"anthropic rejected the request: {e}") from e
            except (anthropic.APIConnectionError, anthropic.RateLimitError, anthropic.InternalServerError) as e:
                raise LLMError(f"anthropic unavailable after retries: {e}") from e
            except anthropic.APIStatusError as e:
                raise LLMError(f"anthropic error {e.status_code}: {e}") from e
            except ValidationError as e:
                # Schema constraints the API can't enforce (e.g. exactly five choices) are checked client-side.
                last_error = e
                log.warning("anthropic returned invalid %s (attempt %d)", schema.__name__, attempt + 1)
                retry = f"{user}\n\nA previous answer failed validation: {e}. Follow the schema exactly."
                messages = [
                    {"role": "user", "content": retry if isinstance(content, str) else content[:-1] + [{"type": "text", "text": retry}]}
                ]
                continue

            if resp.stop_reason == "refusal":
                category = resp.stop_details.category if resp.stop_details else None
                raise LLMError(f"anthropic declined the request (category: {category})")
            if resp.stop_reason == "max_tokens":
                raise LLMError(f"anthropic ran out of output tokens writing {schema.__name__}")
            if resp.parsed_output is None:
                raise LLMError(f"anthropic returned no {schema.__name__}")
            return resp.parsed_output
        raise LLMError(f"anthropic failed to return valid {schema.__name__}: {last_error}")


def make_llm(provider: ProviderConfig, timeout: float) -> StructuredLLM:
    if provider.name == "anthropic":
        return AnthropicLLM(provider, timeout=timeout)
    return OpenAICompatLLM(provider, timeout=timeout)
