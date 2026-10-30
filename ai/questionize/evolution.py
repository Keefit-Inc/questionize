"""A bounded GMAT CR policy cycle: propose with Meta, compare recorded decisions, probe runtime.

No question text or learner identity is accepted by this interface. Replay measures the
decision policy on a development regression set, not fresh inference or learning gains.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import random
import re
import time
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from .eval_e1 import mcnemar, paired_diff_ci, wilson
from .llm import LLMError, StructuredLLM
from .operator_policy import choose_answer
from .schemas import CapabilityPolicy, CapabilityPolicyPayload, Label

GENERATOR_VERSION = "cr-except-proposal-1"
EVALUATOR_VERSION = "cr-decision-replay-1"


def content_hash(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


class StrictModel(BaseModel):
    model_config = {"extra": "forbid"}


class ProposalRequest(StrictModel):
    subject: Literal["CR"] = "CR"
    level: Literal["gmat"] = "gmat"
    baseline: CapabilityPolicyPayload
    observations: dict[str, int | float] = Field(default_factory=dict, max_length=30)

    @model_validator(mode="before")
    @classmethod
    def aggregates_only(cls, value):
        observations = value.get("observations", {}) if isinstance(value, dict) else {}
        if not isinstance(observations, dict) or any(
            not isinstance(key, str) or not re.fullmatch(r"[a-z_]{1,64}", key)
            or isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(number) or number < 0
            for key, number in observations.items()
        ):
            raise ValueError("observations must contain named, finite nonnegative numeric aggregates only")
        return value


class Proposal(StrictModel):
    except_mode: Literal["legacy", "abstain"]
    reason: str = Field(..., min_length=1, max_length=1600)
    hypothesis: str = Field(..., min_length=1, max_length=1200)


PROPOSE_SYSTEM = """You improve one bounded GMAT Critical Reasoning verifier policy.
The blind Solver answers first. For strengthen/weaken/assumption questions an Argument Judge
can override it using a ranking objective selected from the subtype alone. The legacy mapping
does not account for EXCEPT questions: a stable ranking under the wrong objective can replace
a correct answer. The only available change is except_mode: legacy (keep existing behavior)
or abstain (do not apply this subtype-only Judge to stems containing the literal word EXCEPT;
keep the blind Solver and independent Critic). Standard questions remain unchanged.
Use the recorded aggregate evidence to propose a candidate and a falsifiable hypothesis.
Do not claim a candidate is already proven, do not invent results, and do not propose code,
unmeasured prompt changes, question content or additional settings. Return flat JSON fields."""


async def propose(model: StructuredLLM, request: ProposalRequest) -> dict:
    start = time.monotonic()
    try:
        proposal = await asyncio.wait_for(model.complete(PROPOSE_SYSTEM, json.dumps(request.model_dump(), sort_keys=True), Proposal, temperature=0.0), timeout=65)
    except TimeoutError as error:
        raise LLMError("The bounded policy proposal exceeded 65 seconds; the current release was not changed.") from error
    return {
        "payload": {"except_mode": proposal.except_mode}, "reason": proposal.reason, "hypothesis": proposal.hypothesis,
        "model": model.model, "generator_version": GENERATOR_VERSION, "logical_calls": 1,
        "prompt_hash": content_hash({"system": PROPOSE_SYSTEM, "schema": Proposal.model_json_schema()}),
        "duration_seconds": round(time.monotonic() - start, 3),
    }


class ReplayCase(StrictModel):
    case_id: str = Field(..., pattern=r"^[a-zA-Z0-9_-]{8,100}$")
    subtype: str = Field(..., min_length=1, max_length=50)
    operator: Literal["except", "standard"]
    solver_answer: Label
    judge_answer: Label | None = None
    judge_first_rate: float | None = Field(None, ge=0, le=1, allow_inf_nan=False)
    key: Label
    baseline_answer: Label

    @model_validator(mode="after")
    def judge_is_complete(self) -> ReplayCase:
        if (self.judge_answer is None) != (self.judge_first_rate is None):
            raise ValueError("a Judge answer and its first-rate must be recorded together")
        return self


class Benchmark(StrictModel):
    id: str = Field(..., min_length=1, max_length=120)
    hash: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    kind: Literal["decision_replay"]
    cases: list[ReplayCase] = Field(..., min_length=1, max_length=500)

    @model_validator(mode="after")
    def verify_contents(self) -> Benchmark:
        if len({case.case_id for case in self.cases}) != len(self.cases):
            raise ValueError("benchmark contains duplicate case IDs")
        if self.hash != content_hash([case.model_dump() for case in self.cases]):
            raise ValueError("benchmark hash does not match the recorded cases")
        return self


class GateCriteria(StrictModel):
    min_cases: int = Field(35, ge=1, le=500)
    min_improvements: int = Field(1, ge=1, le=500)
    max_regressions: Literal[0] = 0


class EvaluationRequest(StrictModel):
    subject: Literal["CR"] = "CR"
    level: Literal["gmat"] = "gmat"
    baseline: CapabilityPolicy
    candidate: CapabilityPolicy
    benchmark: Benchmark
    criteria: GateCriteria = Field(default_factory=GateCriteria)


class ProbeRequest(StrictModel):
    policy: CapabilityPolicy
    case: ReplayCase
    subject: Literal["CR"] = "CR"
    level: Literal["gmat"] = "gmat"


def case_decision(case: ReplayCase, policy: CapabilityPolicy | None) -> dict:
    return choose_answer(solver_answer=case.solver_answer, judge_answer=case.judge_answer,
                         judge_first_rate=case.judge_first_rate, subtype=case.subtype,
                         operator=case.operator, policy=policy)


def probe(request: ProbeRequest) -> dict:
    result = case_decision(request.case, request.policy)
    return {**result, "runtime": "shared_operator_policy", "evaluator_version": EVALUATOR_VERSION}


def evaluate(request: EvaluationRequest) -> dict:
    cases = request.benchmark.cases
    # The recorded legacy outputs certify this is an actual policy replay, not re-labeled data.
    if any(case_decision(case, None)["chosen_answer"] != case.baseline_answer for case in cases):
        raise ValueError("recorded legacy decisions are not reproduced by the replay benchmark")
    baseline_decisions = [case_decision(case, request.baseline) for case in cases]
    candidate_decisions = [case_decision(case, request.candidate) for case in cases]
    before = {index: decision["chosen_answer"] == case.key for index, (case, decision) in enumerate(zip(cases, baseline_decisions))}
    after = {index: decision["chosen_answer"] == case.key for index, (case, decision) in enumerate(zip(cases, candidate_decisions))}
    paired = mcnemar(before, after)
    standard_changes = sum(case.operator == "standard" and b["chosen_answer"] != c["chosen_answer"] for case, b, c in zip(cases, baseline_decisions, candidate_decisions))
    except_gained = sum(case.operator == "except" and not before[index] and after[index] for index, case in enumerate(cases))
    reasons = []
    if len(cases) < request.criteria.min_cases:
        reasons.append("insufficient_regression_cases")
    if not any(case.operator == "except" for case in cases):
        reasons.append("no_except_coverage")
    if not any(case.operator == "standard" for case in cases):
        reasons.append("no_standard_coverage")
    if request.baseline.payload == request.candidate.payload:
        reasons.append("unchanged_policy")
    if paired["b"] < request.criteria.min_improvements:
        reasons.append("no_measured_improvement")
    if paired["c"]:
        reasons.append("regression_detected")
    if standard_changes:
        reasons.append("standard_decision_changed")
    if not except_gained:
        reasons.append("no_except_regression_fixed")

    def summary(correct):
        k, n = sum(correct.values()), len(correct)
        return {"n": n, "correct": k, "accuracy": round(k / n, 4), "ci95": list(wilson(k, n)), "calls": 0}

    return {
        "evaluation_kind": "decision_replay", "evidence_scope": "development_regression",
        "evaluator_version": EVALUATOR_VERSION, "benchmark_id": request.benchmark.id, "benchmark_hash": request.benchmark.hash,
        "evaluator_hash": hashlib.sha256(Path(__file__).read_bytes() + Path(__file__).with_name("operator_policy.py").read_bytes()).hexdigest(),
        "baseline": summary(before), "candidate": summary(after),
        "comparison": {"gained": paired["b"], "lost": paired["c"], "delta": round((sum(after.values()) - sum(before.values())) / len(cases), 4),
                       "mcnemar_p": paired["p"], "diff_ci95": list(paired_diff_ci(before, after, random.Random(7))),
                       "standard_changes": standard_changes, "standard_regressions": sum(case.operator == "standard" and before[index] and not after[index] for index, case in enumerate(cases)),
                       "except_gained": except_gained},
        "gate": {"passed": not reasons, "reasons": reasons, "criteria": request.criteria.model_dump(),
                 "interpretation": "Narrow decision-policy regression gate; not fresh model accuracy or learner-growth evidence."},
        "proofs": [{"case_id": case.case_id, "operator": case.operator, "baseline_answer": b["chosen_answer"],
                    "candidate_answer": c["chosen_answer"], "key": case.key, "judge_abstained": c["judge_abstained"]}
                   for case, b, c in zip(cases, baseline_decisions, candidate_decisions)],
    }
