"""Publish E14 aggregate evidence, never the private source/results artifact.

python -m questionize.publish_budget_cr --experiment PRIVATE_DIRECTORY
"""
import argparse
import collections
import json
from pathlib import Path

from .budget_report import project_study
from .audit_budget_cr import audit
from .eval_budget_cr import summarise

RESEARCH = Path(__file__).resolve().parents[2] / "research"
LABELS = {"A": "Meta baseline", "M": "Training-derived memory", "MV": "Memory + verifier"}


def percent(value): return f"{100*value:.2f}%"
def money(value): return f"${value:.6f}"


def render(entry):
    study = entry["budget_study"]; summary = study["conditions"]; split = study["split"]; d = study["diagnostics"]
    out = ["# E14 v1 — GMAT CR memory and verification under equal budgets", "",
           "## Outcome", "",
           ("A positive observed MV gain requires independent confirmation; the research candidate is not deployed."
            if study["decision"] == "confirmation_required" else "Hold this research candidate. A cost-valid, error-free improvement over the baseline was not established."), "",
           f"Run: `{entry['run_id']}`. Source/code commit: `{entry['git_sha']}`. Final evaluation completed before this aggregate was published.", "",
           "## Frozen source separation", "",
           "| Partition | Questions | Stimulus groups | Membership SHA-256 |", "|---|---:|---:|---|"]
    for name in ("train", "development", "test", "held"):
        out.append(f"| {name} | {split['counts'][name]} | {split['groups'][name]} | `{split['membership_hashes'][name]}` |")
    out += ["", f"Cross-partition exact/near-stimulus overlap after screening: {split['cross_partition_group_overlap']}. The key-only compilation is excluded.",
            "The original OG training membership supplies the teacher context. Previously inspected OG test/completion records remain development-only. New explanation-backed source material supplies the final test. All source originals, keys, reference explanations, learned procedures and individual outputs remain private/local.", "",
            f"Request-hash blinding audit: **{study.get('blinding_audit',{}).get('passed',False)}**. Training requests matched {study.get('blinding_audit',{}).get('training_requests_matched',0)}/{study.get('blinding_audit',{}).get('training_requests_checked',0)}; final evaluation requests matched {study.get('blinding_audit',{}).get('evaluation_requests_matched',0)}/{study.get('blinding_audit',{}).get('evaluation_requests_checked',0)}. The reconstruction uses training-only teacher inputs and explicit question-only blind Solver inputs; the verifier may additionally receive the first public answer/rationale. This checks recorded request construction, not model pretraining exposure.", "",
            "## Conditions and cost accounting", "",
            f"Standard `{study['model']}`, Responses API, reasoning effort `{study['reasoning_effort']}`, no tools, `store=false`, no generation retries. Each condition has a {money(study['envelope_usd'])} per-item **uncached token-price ceiling**. A is one production-instruction Solver call; M adds a frozen training-derived procedure; MV allocates half the envelope to its first memory Solver and the unspent balance to a separate verifier call.",
            "The verifier sees the proposed public answer/rationale, never the reference key or source explanation. It uses the same model; separate calls are not independently trained evaluators.", "",
            "The envelope is equal, not necessarily actual expenditure. Preflight context counts reserve input conservatively; response usage supplies token accounting. Normalised spend prices all input uncached, preventing prompt-cache order from expanding the envelope. Estimated billed spend discounts reported cache hits. Hidden reasoning is included once in output tokens. Latency includes token preflight and generation. Account-level invoices and unrelated production traffic are not measured.", "",
            "| Condition | Correct / n | Accuracy | Wilson 95% interval | Generation calls | Normalised spend | Estimated billed | Mean item seconds | Errors |",
            "|---|---:|---:|---|---:|---:|---:|---:|---:|"]
    for arm, row in summary.items():
        out.append(f"| {arm}: {LABELS[arm]} | {row['correct']}/{row['n']} | {percent(row['accuracy'])} | {percent(row['ci95'][0])}–{percent(row['ci95'][1])} | {row['calls']} | {money(row['normalised_usd'])} | {money(row['estimated_billed_usd'])} | {row['mean_seconds']:.2f} | {row['errors']} |")
    out += ["", f"Cost comparison valid under the registered accounting rule: **{study['cost_comparison_valid']}**.",
            f"Procedure construction: {study['training_calls']} calls, {money(study['training_normalised_usd'])} normalised / {money(study['training_estimated_billed_usd'])} estimated billed; {study['procedure_count']} usable subtype procedures, {study['training_failures']} rejected/failed constructions. This is a separate one-time cost, not free training.",
            f"Development smoke: {study.get('development_calls',0)} calls, {money(study.get('development_normalised_usd',0))} normalised / {money(study.get('development_estimated_billed_usd',0))} estimated billed.",
            f"Stem-based routing retrieved a learned procedure for {study.get('memory_retrieval_covered',0)}/{split['counts']['test']} final items; unrecognised stems get the baseline instruction. Source subtype metadata is not provided to the Solver.", "",
            "Rates reviewed 2026-10-30: $1.25/M input, $0.15/M cached input, $4.25/M output. [Meta pricing](https://dev.meta.ai/docs/pricing-rate-limits), [token counting](https://dev.meta.ai/docs/token-counting), [reasoning controls](https://dev.meta.ai/docs/reasoning).", "",
            "## Paired comparisons", "", "| Against A | Gained | Lost | Difference | Group-bootstrap 95% interval | Exact McNemar p |", "|---|---:|---:|---:|---|---:|"]
    for arm in ("M", "MV"):
        c = summary[arm]["vs_baseline"]
        out.append(f"| {arm} | {c['b']} | {c['c']} | {100*c['difference']:+.2f} pp | {100*c['diff_ci95'][0]:+.2f} to {100*c['diff_ci95'][1]:+.2f} pp | {c['p']} |")
    out += ["", "Operational error categories (post-run metadata diagnosis; no outcome reruns):",
            *[f"- {arm}: " + (", ".join(f"{kind}={count}" for kind,count in counts.items()) or "none")
              for arm,counts in study.get("operational_errors",{}).items()]]
    out += ["", "Comparisons are descriptive for this fixed sample, not multiple-testing-adjusted population superiority claims. All registered items remain in the denominator, including errors; no post-result retries or exclusions. An empirical zero-width difference interval from identical outcomes does not prove a population effect of zero.",
            "A and M use identical instructions on stems for which no procedure is retrieved; differences there can reflect inference variation. The one-pass design requires independent confirmation even when the observed difference is positive.", "",
            "## Solver versus verifier bottleneck", "",
            f"Within MV: both correct **{d['both_correct']}**; wrong→right rescue **{d['rescue']}**; right→wrong harm **{d['harm']}**; both wrong **{d['both_wrong']}**; operational error **{d['operational_error']}**.",
            "These transitions compare MV's first Solver and its verifier, not A with MV. A correct first answer replaced by an incorrect final answer directly demonstrates a verification/selection failure. When neither answer matches the source, the configured proposal/verification procedure still lacks a correct candidate; that does not establish a fundamental model ceiling or prove fine-tuning necessary. Source-label errors remain possible. Any oracle choosing the correct candidate uses information unavailable in production and is only a diagnostic.", "",
            "## Predefined stem-type slices", "", "| Stem-routed type | n | A correct | M correct | MV correct |", "|---|---:|---:|---:|---:|"]
    for name, row in study["slices"].items(): out.append(f"| {name} | {row['n']} | {row['A']} | {row['M']} | {row['MV']} |")
    out += ["", "## Artifact provenance and interpretation", ""]
    for name in ("memory_hash", "manifest_hash", "runner_hash", "client_hash"): out.append(f"- {name}: `{study[name]}`")
    out += ["", "No research candidate was deployed. Running service memory/policy versions remain separately visible in the Upload learning console. A positive finding requires a new confirmation study; a null or losing finding remains held. Final failures may inform a future development set, never a claim that this same test remains untouched.",
            "This measures source-key agreement on published practice sources, not independently human-adjudicated truth. Possible pretraining exposure, source-quality differences, a single inference pass, correlated model errors and small subtype samples limit generalisation. Exact/five-gram deduplication cannot certify semantic independence. No human explanation ratings, generated-item quality or learner-growth result is claimed.", "",
            "The structured-context idea is informed by [GEPA](https://arxiv.org/abs/2507.19457) and [ACE](https://arxiv.org/abs/2510.04618). This experiment does not implement their full optimisation algorithms or reproduce their benchmark gains.", "",
            "[Registered protocol](../protocols/E14-budget-matched-reasoning.md) · [post-run diagnostic annotation](E14-diagnostics.md) · [metered client](../../ai/questionize/research_budget.py) · [runner](../../ai/questionize/eval_budget_cr.py) · [public console](https://questionize.org/admin#budget)", ""]
    return "\n".join(out)


def publish(root, research=RESEARCH):
    entry = summarise(root)
    entry["budget_study"]["blinding_audit"] = audit(root)
    if not entry["budget_study"]["blinding_audit"]["passed"]: entry["budget_study"]["decision"] = "held"
    private_run = json.loads((root / "test.json").read_text())
    operational = {arm: collections.Counter() for arm in LABELS}
    for row in private_run["rows"]:
        for arm,result in row["conditions"].items():
            error = result["error"]
            if not error: continue
            last = result["calls"][-1] if result["calls"] else {}
            if error == "incomplete_response" and last.get("output_tokens",0) >= last.get("max_output_tokens",float("inf")):
                kind = "output_budget_exhausted"
            elif error in ("ValidationError", "JSONDecodeError"): kind = "schema"
            elif error.startswith("http_") or error.endswith("Timeout"): kind = "provider"
            elif error in ("budget_exceeded", "insufficient_budget"): kind = "budget"
            elif error in ("missing_usage", "invalid_usage"): kind = "accounting"
            elif error == "incomplete_response": kind = "incomplete"
            else: kind = "other"
            operational[arm][kind] += 1
    entry["budget_study"]["operational_errors"] = {arm:dict(counts) for arm,counts in operational.items()}
    study = project_study(entry)
    # Field-level projection also protects the public ledger, not only the dashboard export.
    entry["budget_study"] = study
    entry["summary"] = study["conditions"]
    ledger = research / "ledger.jsonl"
    existing = [json.loads(line) for line in ledger.read_text().splitlines() if line.strip()] if ledger.exists() else []
    matches = [row for row in existing if row.get("run_id") == entry["run_id"]]
    if matches and matches != [entry]: raise ValueError("An existing ledger entry differs; append a correction, never overwrite it")
    if not matches:
        with ledger.open("a") as handle: handle.write(json.dumps(entry,ensure_ascii=False,allow_nan=False) + "\n")
    (research / "results").mkdir(exist_ok=True)
    (research / "results/E14.md").write_text(render(entry))
    print(json.dumps({"run_id":entry["run_id"],"decision":study["decision"],"conditions":{a:{k:r[k] for k in ('n','correct','normalised_usd','estimated_billed_usd','errors')} for a,r in study["conditions"].items()},"diagnostics":study["diagnostics"]}))


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--experiment",type=Path,required=True);args=parser.parse_args()
    publish(args.experiment)
