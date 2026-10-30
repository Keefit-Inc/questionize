"""Versioned, bounded verifier policy shared by replay evaluation and live requests.

This first policy does not claim to understand every negative question. It recognizes the
literal EXCEPT operator in a question stem and can abstain from applying a subtype-only Judge.
"""

from __future__ import annotations

import re

from .judge import SUBTYPE_MEASURES
from .schemas import CapabilityPolicy

OVERRIDE_FIRST_RATE = 0.8


def task_operator(stem: str) -> str:
    return "except" if re.search(r"\bEXCEPT\b", stem, flags=re.IGNORECASE) else "standard"


def policy_trace(policy: CapabilityPolicy | None, *, subject: str, level: str, subtype: str, operator: str) -> dict:
    in_scope = subject == "CR" and level == "gmat"
    abstain = bool(policy and in_scope and subtype in SUBTYPE_MEASURES and operator == "except" and policy.payload.except_mode == "abstain")
    return {
        "policy_id": policy.id if policy else None,
        "policy_hash": policy.hash if policy else None,
        "operator": operator,
        "applied": bool(policy and in_scope),
        "judge_abstained": abstain,
        "reason": "unsupported_except_objective" if abstain else "subtype_policy" if in_scope else "outside_policy_scope",
    }


def choose_answer(*, solver_answer: str, judge_answer: str | None, judge_first_rate: float | None, subtype: str,
                  operator: str, policy: CapabilityPolicy | None, subject: str = "CR", level: str = "gmat") -> dict:
    """Apply the same admissibility guard used before the live Judge is called."""
    trace = policy_trace(policy, subject=subject, level=level, subtype=subtype, operator=operator)
    use_judge = bool(subtype in SUBTYPE_MEASURES and judge_answer and judge_first_rate is not None
                     and judge_first_rate >= OVERRIDE_FIRST_RATE and not trace["judge_abstained"])
    answer = judge_answer if use_judge else solver_answer
    return {"chosen_answer": answer, **trace, "judge_used": use_judge, "overrode_solver": answer != solver_answer}
