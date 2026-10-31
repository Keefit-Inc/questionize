"""Explicit aggregate projection for E14; never forward private experiment objects."""
import math
import re

PARTITIONS = ("train", "development", "test", "held")
ARMS = ("A", "M", "MV")
TYPES = ("strengthen", "weaken", "assumption", "inference", "evaluate", "explain", "flaw", "structure", "unknown")


def numeric(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def fields(obj, names):
    return {k: obj[k] for k in names if numeric(obj.get(k))}


def hashes(obj, names):
    return {k: obj[k] for k in names if isinstance(obj.get(k), str) and re.fullmatch(r"[a-f0-9]{64}", obj[k])}


def project_study(row):
    value = row.get("budget_study")
    if row.get("protocol") != "E14" or not isinstance(value, dict) or value.get("schema_version") != 1:
        return None
    result = {"schema_version": 1, "run_id": row["run_id"], "started_at": row.get("started_at"),
              "model": "muse-spark-1.3", "reasoning_effort": "medium",
              "decision": value.get("decision") if value.get("decision") in ("held", "confirmation_required") else "held",
              "candidate_deployed": False, "price_url": "https://dev.meta.ai/docs/pricing-rate-limits",
              "price_reviewed": "2026-10-30", "report_path": "research/results/E14.md",
              "protocol_path": "research/protocols/E14-budget-matched-reasoning.md"}
    result.update(fields(value, ("envelope_usd", "training_normalised_usd", "training_estimated_billed_usd", "training_calls",
                                  "training_failures", "procedure_count", "development_normalised_usd", "development_estimated_billed_usd", "development_calls", "memory_retrieval_covered")))
    result.update(hashes(value, ("memory_hash", "manifest_hash", "runner_hash", "client_hash")))
    result["cost_comparison_valid"] = value.get("cost_comparison_valid") is True
    result["rates"] = fields(value.get("rates", {}), ("input", "cached_input", "output"))
    split = value.get("split", {})
    result["split"] = {"counts": fields(split.get("counts", {}), PARTITIONS), "groups": fields(split.get("groups", {}), PARTITIONS),
                       "membership_hashes": hashes(split.get("membership_hashes", {}), PARTITIONS),
                       **fields(split, ("overlap_links", "cross_partition_group_overlap")), "key_only_compilation_used": False}
    result["conditions"] = {}
    for name in ARMS:
        obj = value.get("conditions", {}).get(name, {})
        projected = fields(obj, ("n", "expected_n", "correct", "accuracy", "errors", "calls", "normalised_usd", "estimated_billed_usd",
                                  "input_tokens", "output_tokens", "reasoning_tokens", "cached_tokens", "mean_seconds", "budget_violations"))
        projected["usage_complete"] = obj.get("usage_complete") is True
        ci = obj.get("ci95")
        if isinstance(ci, list) and len(ci) == 2 and all(numeric(n) for n in ci): projected["ci95"] = ci
        comparison = obj.get("vs_baseline", {})
        projected["vs_baseline"] = fields(comparison, ("b", "c", "p", "n", "difference", "baseline_accuracy"))
        ci = comparison.get("diff_ci95")
        if isinstance(ci, list) and len(ci) == 2 and all(numeric(n) for n in ci): projected["vs_baseline"]["diff_ci95"] = ci
        result["conditions"][name] = projected
    result["diagnostics"] = fields(value.get("diagnostics", {}), ("both_correct", "rescue", "harm", "both_wrong", "operational_error", "oracle_opportunity_missed", "first_solver_wrong"))
    result["slices"] = {name: fields(obj, ("n", *ARMS)) for name, obj in value.get("slices", {}).items() if name in TYPES and isinstance(obj, dict)}
    return result
