"""Thin structured-output client over any OpenAI-compatible endpoint.

Both the Meta Model API and Baseten expose the OpenAI Chat Completions
protocol, so one client covers Muse Spark (hosted) and Muse Spark Open.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Protocol, TypeVar

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

    async def complete(self, system: str, user: str, schema: type[T], *, temperature: float = 0.4) -> T: ...


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
                f"No API key for provider '{provider.name}'. Set it in server/.env (see .env.example)."
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

    async def complete(self, system: str, user: str, schema: type[T], *, temperature: float = 0.4) -> T:
        schema_hint = json.dumps(schema.model_json_schema())
        messages = [
            {
                "role": "system",
                "content": f"{system}\n\nRespond with a single JSON object matching this JSON Schema:\n{schema_hint}",
            },
            {"role": "user", "content": user},
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
