"""Metered, no-retry Meta research calls with an equal uncached-dollar envelope.

This research-only client does not change the production LLM configuration.
Preflight context counts conservatively reserve input; only response usage is billing data.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from decimal import Decimal

import httpx
from pydantic import BaseModel

from .llm import parse_structured

RATES = {"input": 1.25, "cached_input": .15, "output": 4.25}
MODEL_RATES = {"muse-spark-1.3": RATES, "muse-wonder-1.0": {"input": 4.0, "cached_input": .20, "output": 20.0}}
PRICE_URL = "https://dev.meta.ai/docs/pricing-rate-limits"
PRICE_REVIEWED = "2026-10-30"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def price(input_tokens, output_tokens, cached_tokens=0, rates=None):
    rates = rates or RATES
    if not 0 <= cached_tokens <= input_tokens or min(input_tokens, output_tokens) < 0:
        raise ValueError("Invalid token accounting")
    return round(((input_tokens - cached_tokens) * rates["input"] + cached_tokens * rates["cached_input"]
                  + output_tokens * rates["output"]) / 1_000_000, 9)


def output_limit(allowance, context_tokens, maximum=16000, rates=None):
    rates = rates or RATES
    available = Decimal(str(allowance)) - Decimal(context_tokens) * Decimal(str(rates["input"])) / 1_000_000
    return max(0, min(maximum, math.floor(available * 1_000_000 / Decimal(str(rates["output"])))))


class BudgetFailure(RuntimeError):
    def __init__(self, reason, metrics):
        super().__init__(reason)
        self.reason, self.metrics = reason, metrics


class BudgetClient:
    def __init__(self, provider, *, transport=None, effort="medium", audit=None):
        if provider.name != "meta" or provider.model not in MODEL_RATES:
            raise ValueError("Research requires a registered Standard Meta model and verified rates")
        self.model, self.effort = provider.model, effort
        self.rates, self.audit = MODEL_RATES[self.model], audit
        self.http = httpx.AsyncClient(base_url=provider.base_url.rstrip("/") + "/",
            headers={"Authorization": "Bearer " + provider.api_key}, timeout=180, transport=transport)

    async def close(self):
        await self.http.aclose()

    async def complete(self, system, user, schema: type[BaseModel], allowance, *, maximum=16000):
        body = {"model": self.model, "input": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "reasoning": {"effort": self.effort}, "store": False,
                "text": {"format": {"type": "json_schema", "name": schema.__name__, "strict": True,
                                    "schema": schema.model_json_schema()}}}
        metrics = {"request_hash": digest(body), "allowance_usd": allowance, "generation_calls": 0,
                   "input_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0, "cached_tokens": 0,
                   "normalised_usd": 0., "estimated_billed_usd": 0., "usage_complete": False}
        start = time.monotonic()
        try:
            count = await self.http.post("responses/input_tokens", json=body)
            count.raise_for_status()
            context = count.json()["input_tokens"]
            if not isinstance(context, int) or isinstance(context, bool) or context < 0:
                raise ValueError("Invalid preflight count")
            cap = output_limit(allowance, context, maximum, self.rates)
            metrics.update(preflight_context_tokens=context, max_output_tokens=cap)
            if cap < 512:
                raise BudgetFailure("insufficient_budget", metrics)
            metrics["generation_calls"] = 1
            response = await self.http.post("responses", json={**body, "max_output_tokens": cap})
            response.raise_for_status()
            data = response.json()
            if self.audit:
                self.audit({"request_hash":metrics["request_hash"], "response":data})
            metrics.update(response_id=data.get("id"), response_status=data.get("status"),
                           incomplete_reason=(data.get("incomplete_details") or {}).get("reason"))
            usage = data.get("usage") or {}
            inp, out = usage.get("input_tokens"), usage.get("output_tokens")
            cached = (usage.get("input_tokens_details") or {}).get("cached_tokens", 0)
            reasoning = (usage.get("output_tokens_details") or {}).get("reasoning_tokens", 0)
            if not all(isinstance(v, int) and not isinstance(v, bool) and v >= 0 for v in (inp, out, cached, reasoning)):
                raise BudgetFailure("missing_usage", metrics)
            if reasoning > out:
                raise BudgetFailure("invalid_usage", metrics)
            metrics.update(input_tokens=inp, output_tokens=out, cached_tokens=cached, reasoning_tokens=reasoning,
                           normalised_usd=price(inp, out, rates=self.rates), estimated_billed_usd=price(inp, out, cached, self.rates), usage_complete=True,
                           response_model=data.get("model", self.model))
            if metrics["normalised_usd"] > allowance + 0.000001:
                raise BudgetFailure("budget_exceeded", metrics)
            if data.get("status") != "completed":
                raise BudgetFailure("incomplete_response", metrics)
            content = "".join(part.get("text", "") for item in data.get("output", [])
                              if item.get("type") == "message" for part in item.get("content", [])
                              if part.get("type") == "output_text")
            result = parse_structured(content, schema)
            metrics["elapsed_seconds"] = round(time.monotonic() - start, 3)
            return result, metrics
        except BudgetFailure:
            raise
        except Exception as error:
            # Provider messages may contain source text. Retain only a bounded error category here.
            status = getattr(getattr(error, "response", None), "status_code", None)
            raise BudgetFailure(f"http_{status}" if status else type(error).__name__, metrics) from None
        finally:
            metrics["elapsed_seconds"] = round(time.monotonic() - start, 3)
