"""Generate capability-specific research reports and aggregate-only dashboard data.

    python -m questionize.scoreboard

Reads the append-only ledger without changing it. Full evaluations and trials are kept separate;
claiming a capability in a run does not make another capability's metric evidence for it.
"""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

RESEARCH = Path(__file__).resolve().parents[2] / "research"
LEDGER = RESEARCH / "ledger.jsonl"

CAPABILITIES: list[tuple[str, str, str]] = [
    ("C1.1", "Capture: extract", "items with every role right ≥ 98%; CER ≤ 1% scans, ≤ 2% photos"),
    ("C1.2", "Capture: reconstruct", "solvability equivalence ≥ 95% on items with figures"),
    ("C2", "Understand the item", "skill agreement ≥ 90%; trap tags ≥ 80%; difficulty ρ ≥ 0.4"),
    ("C3.1", "Solve", "accuracy against the key ≥ 95% (CR)"),
    ("C3.2", "Explain", "explanations rated correct ≥ 90%"),
    ("C3.3", "Explain at the learner's level", "readability in band ≥ 90%; preferred to generic"),
    ("C3.4", "Validate candidate correctness", "reject constructed defects; report valid-control rejection and parent clustering separately"),
    ("C4", "Diagnose the learner", "misconception top-3 ≥ 70%; next-miss AUC ≥ 0.65"),
    ("C5", "Write practice", "first-draft verification rate rising with memory; two-answer rate ≤ 2%"),
    ("C6", "Choose practice", "success on recommended 60%–80%; gains over unrecommended"),
]

# A scalar `primary` is ambiguous when a run declares several capabilities. New runners can
# report summary[condition].capability_metrics[capability] = {value, n, ci95}; otherwise only
# the specifically named metric below is accepted. E1's accuracy measures C3.1, never C3.2.
METRICS = {
    "C1.1": "role_accuracy",
    "C1.2": "solvability_equivalence",
    "C2": "skill_agreement",
    "C3.1": "accuracy",
    "C3.2": "explanation_correctness",
    "C3.3": "readability_in_band",
    "C3.4": "defect_rejection_rate",
    "C4": "misconception_top3",
    "C5": "first_draft_pass_rate",
    "C6": "recommendation_success_rate",
}


def load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    invalid = {r["invalidates"] for r in rows if r.get("invalidates")}
    return [r for r in rows if r.get("run_id") and r["run_id"] not in invalid and not r.get("invalidates")]


def subject_of(run: dict) -> str:
    """Runs before the subject field was introduced measured CR."""
    return run.get("subject") or "CR"


def scope_of(run: dict) -> str:
    """Honor explicit scope; recognize legacy trial notes without guessing from sample size."""
    explicit = run.get("evaluation_scope") or run.get("scope") or run.get("run_kind")
    if explicit in ("trial", "pilot", "smoke", "development"):
        return "trial"
    if explicit == "full":
        return "full"
    if explicit == "regression":
        return "regression"
    if run.get("limit") or run.get("item_limit"):
        return "trial"
    return "trial" if re.search(r"\b(trial|pilot|smoke)\b", run.get("note") or "", re.IGNORECASE) else "full"


def number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def confidence_interval(value: Any) -> list[float] | None:
    if isinstance(value, (list, tuple)) and len(value) == 2 and all(number(n) for n in value):
        return list(value)
    return None


def count(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def metric_for(summary: dict, capability: str) -> dict | None:
    """Return only the primary measure actually reported for this capability."""
    metrics = summary.get("capability_metrics")
    specific = metrics.get(capability) if isinstance(metrics, dict) else None
    if isinstance(specific, dict) and number(specific.get("value")):
        return {"value": specific["value"], "n": count(specific.get("n")), "ci95": confidence_interval(specific.get("ci95"))}
    metric = METRICS.get(capability)
    value = summary.get(metric) if metric else None
    if isinstance(value, dict) and number(value.get("value")):
        return {"value": value["value"], "n": count(value.get("n")), "ci95": confidence_interval(value.get("ci95"))}
    if number(value):
        # A non-solving metric's interval/count must be named with it, so a solve CI or total
        # response count cannot accidentally become the human-rating interval or rated count.
        return {
            "value": value,
            "n": count(summary.get("n" if capability == "C3.1" else f"{metric}_n")),
            "ci95": confidence_interval(summary.get("ci95" if capability == "C3.1" else f"{metric}_ci95")),
        }
    return None


def _format(value: float) -> str:
    short = f"{value:.2f}"
    return short if abs(float(short) - value) < 1e-9 else f"{value:.4f}"


def headline(summary: dict, capability: str = "C3.1") -> str:
    parts = []
    for cond, m in summary.items():
        if not isinstance(m, dict):
            continue
        measured = metric_for(m, capability)
        if measured is None:
            continue
        value, ci, n = measured["value"], measured["ci95"], measured["n"]
        parts.append(f"{cond} {_format(value)}" + (f" [{_format(ci[0])}, {_format(ci[1])}]" if ci else "") + f" (n={n if n is not None else '?'})")
    return " · ".join(parts) or "not measured yet"


def _cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def qualifications_for(run: dict, definitions: dict | None = None) -> list[dict]:
    """Project matching public annotations, never fields supplied on the run itself."""
    if definitions is None:
        return []
    if not isinstance(definitions, dict) or definitions.get("schema_version") != 1 or not isinstance(definitions.get("qualifications"), list):
        raise ValueError("Unsupported qualifications schema")
    matches = []
    for entry in definitions["qualifications"]:
        if not isinstance(entry, dict):
            continue
        selector = entry.get("applies_to")
        if not isinstance(selector, dict) or not selector or set(selector) - {"dataset_hash", "protocol", "protocol_version"}:
            continue
        if ("protocol" in selector) != ("protocol_version" in selector):
            continue
        if "protocol_version" in selector and (not isinstance(selector["protocol_version"], int) or isinstance(selector["protocol_version"], bool) or selector["protocol_version"] < 1):
            continue
        if any(not isinstance(selector[key], str) or not selector[key] for key in ("dataset_hash", "protocol") if key in selector):
            continue
        if any(run.get(key) != value for key, value in selector.items()):
            continue
        if not all(isinstance(entry.get(key), str) and entry[key].strip() for key in ("id", "summary")):
            continue
        item = {"id": entry["id"], "summary": entry["summary"]}
        report_url = entry.get("report_url")
        if isinstance(report_url, str) and not re.search(r"\s", report_url):
            try:
                url = urlsplit(report_url)
            except ValueError:
                url = None
            if url and url.scheme == "https" and url.netloc == "github.com" and url.path.startswith("/Keefit-Inc/questionize/blob/") and any(folder in url.path for folder in ("/research/results/", "/research/protocols/")) and not url.query:
                item["report_url"] = report_url
        matches.append(item)
    # Input ordering or repeated annotations cannot change the published snapshot.
    unique = {}
    for item in sorted(matches, key=lambda item: (item["id"], item["summary"], item.get("report_url", ""))):
        unique.setdefault(item["id"], item)
    return [unique[key] for key in sorted(unique)]


def _qualification_notes(rows: list[dict], definitions: dict | None) -> list[str]:
    matched = {q["id"]: q for row in rows for q in qualifications_for(row, definitions)}
    if not matched:
        return []
    out = ["", "## Data and method qualifications", "", "These annotations qualify interpretation; the recorded results and runs are retained.", ""]
    for key in sorted(matched):
        item = matched[key]
        report = f" [Report]({item['report_url']})" if item.get("report_url") else ""
        out.append(f"- **{item['id']}:** {item['summary']}{report}")
    return out


def render(rows: list[dict], qualifications: dict | None = None) -> str:
    out = [
        "# Scoreboard", "",
        "Generated from `research/ledger.jsonl` by `python -m questionize.scoreboard`; do not edit by hand. "
        "Full evaluations and trials are separate. Each row shows only its capability's own metric; "
        "solving accuracy is not an explanation rating. Bars from research/README.md.", "",
        "| Capability | Subject | Scope | Bar | Latest result | Run |",
        "|---|---|---|---|---|---|",
    ]
    for cap, name, bar in CAPABILITIES:
        runs = [r for r in rows if cap in r.get("capabilities", [])]
        subjects = sorted({subject_of(r) for r in runs}) or [""]
        for subject in subjects:
            mine = [r for r in runs if subject_of(r) == subject]
            scopes = [s for s in ("full", "trial", "regression") if any(scope_of(r) == s for r in mine)] or [""]
            for scope in scopes:
                candidates = [r for r in mine if scope_of(r) == scope]
                # Pending ratings must not hide earlier completed ratings in the same scope.
                measured = [r for r in candidates if headline(r.get("summary", {}), cap) != "not measured yet"]
                if measured:
                    r = max(measured, key=lambda r: (r.get("started_at", ""), r["run_id"]))
                    result = headline(r.get("summary", {}), cap)
                    run = f"{r['protocol']} v{r.get('protocol_version', 1)} · {r['run_id']} · {', '.join(r.get('models', {}).values())}"
                    if qualifications_for(r, qualifications):
                        run += " · provisional (see qualifications)"
                else:
                    result, run = "not measured yet", ""
                out.append("| " + " | ".join(_cell(x) for x in (f"{cap} {name}", subject, scope, bar, result, run)) + " |")
    out.extend(_qualification_notes(rows, qualifications))
    return "\n".join(out) + "\n"


def history(rows: list[dict], capability: str, qualifications: dict | None = None) -> str:
    """All valid runs in the capability family, including trials and unmeasured sub-capabilities."""
    runs = sorted((r for r in rows if any(c.split(".")[0] == capability for c in r.get("capabilities", []))), key=lambda r: (r.get("started_at", ""), r["run_id"]))
    out = [
        f"# {capability} improvement history", "",
        "Generated from `research/ledger.jsonl` by `python -m questionize.scoreboard`; do not edit by hand. "
        "Trials remain visible and are not full evaluations. Each sub-capability uses its own metric; "
        "these observations do not automatically establish an improvement.", "",
        "| Date | Subject | Scope | Run | Protocol | What changed | Models | Result |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in runs:
        caps = [c for c, _, _ in CAPABILITIES if c in r.get("capabilities", []) and c.split(".")[0] == capability]
        result = "; ".join(f"{c}: {headline(r.get('summary', {}), c)}" for c in caps)
        if qualifications_for(r, qualifications):
            result += "; provisional (see qualifications)"
        values = (r.get("started_at", "")[:10], subject_of(r), scope_of(r), r["run_id"], f"{r['protocol']} v{r.get('protocol_version', 1)}", r.get("note") or "", ", ".join(r.get("models", {}).values()), result)
        out.append("| " + " | ".join(_cell(v) for v in values) + " |")
    if not runs:
        out.append("| | | | | | not measured yet | | |")
    out.extend(_qualification_notes(runs, qualifications))
    return "\n".join(out) + "\n"


def _numeric_fields(source: Any, names: tuple[str, ...]) -> dict:
    if not isinstance(source, dict):
        return {}
    return {name: source[name] for name in names if number(source.get(name))}


def _comparison(source: Any) -> dict | None:
    if not isinstance(source, dict):
        return None
    result = _numeric_fields(source, ("b", "c", "p", "n", "baseline_accuracy"))
    ci = confidence_interval(source.get("diff_ci95"))
    if ci is not None:
        result["diff_ci95"] = ci
    return result or None


def render_data(rows: list[dict], qualifications: dict | None = None) -> dict:
    """Deterministic aggregate-only schema v1; no raw ledger passthrough.

    `runs` contains the comparison context: dataset/hash, split, prompts/hash, models, judge,
    memory/hash and requested n_items. `records` contains a metric for one capability and
    condition with its actual n, expected_n and completeness. Compare contexts explicitly;
    the exporter never promotes a run or declares mismatched contexts comparable. Public
    qualifications are passed explicitly; this function never reads annotation or private files.
    """
    qualifications_for({}, qualifications)  # validate the schema even when there are no runs
    runs, records = [], []
    for row in sorted(rows, key=lambda r: (r.get("started_at", ""), r["run_id"])):
        run = {
            name: row[name] for name in ("run_id", "protocol", "protocol_version", "started_at", "git_sha", "prompts_hash", "dataset_id", "dataset_hash", "split", "n_items", "baseline_run", "note")
            if name in row and isinstance(row[name], (str, int, float, type(None)))
        }
        run.update({
            "subject": subject_of(row), "scope": scope_of(row),
            "capabilities": [c for c, _, _ in CAPABILITIES if c in row.get("capabilities", [])],
            "models": {k: v for k, v in row.get("models", {}).items() if isinstance(k, str) and isinstance(v, str)},
            "qualifications": qualifications_for(row, qualifications),
        })
        judge = row.get("judge")
        if isinstance(judge, dict):
            run["judge"] = _numeric_fields(judge, ("samples_per_judge", "override_rate"))
            if isinstance(judge.get("version"), str):
                run["judge"]["version"] = judge["version"]
        memory = row.get("memory")
        run["memory"] = None
        if isinstance(memory, dict):
            run["memory"] = _numeric_fields(memory, ("lessons",))
            if isinstance(memory.get("hash"), str):
                run["memory"]["hash"] = memory["hash"]
        for cap in run["capabilities"]:
            for condition, result in sorted(row.get("summary", {}).items()):
                if not isinstance(result, dict):
                    continue
                measured = metric_for(result, cap)
                if measured is None:
                    continue
                n = measured["n"]
                expected = count(result.get("expected_n", row.get("n_items")))
                record = {
                    "run_id": row["run_id"], "capability": cap, "subject": run["subject"], "condition": condition,
                    "scope": run["scope"], "metric": METRICS[cap], **measured, "expected_n": expected,
                    "complete": n == expected if number(n) and number(expected) else None,
                }
                record.update(_numeric_fields(result, ("calls", "ece")))
                for name in ("vs_B0", "vs_baseline"):
                    comparison = _comparison(result.get(name))
                    if comparison is not None:
                        record[name] = comparison
                records.append(record)
        run["measured_capabilities"] = sorted({r["capability"] for r in records if r["run_id"] == row["run_id"]})
        runs.append(run)
    from .budget_report import project_study
    from .mastery_report import project as project_mastery
    return {
        "schema_version": 1,
        "updated_at": max((r.get("started_at", "") for r in runs), default=None),
        "capabilities": [{"id": cap, "name": name, "bar": bar, "metric": METRICS[cap], "unit": "ratio", "direction": "target" if cap == "C6" else "higher"} for cap, name, bar in CAPABILITIES],
        "subjects": sorted({r["subject"] for r in runs}),
        "runs": runs,
        "records": records,
        "budget_studies": [study for row in rows if (study := project_study(row)) is not None],
        "mastery_studies": [study for row in rows if (study := project_mastery(row)) is not None],
    }


def write_all(rows: list[dict], research: Path = RESEARCH) -> list[Path]:
    qualification_path = research / "qualifications.json"
    qualifications = json.loads(qualification_path.read_text()) if qualification_path.is_file() else None
    dashboard = render_data(rows, qualifications)
    registry = research / "evidence-map.json"
    if registry.is_file():
        from .research_map import project_registry
        dashboard["evidence"] = project_registry(json.loads(registry.read_text()), rows)
    (research / "results").mkdir(parents=True, exist_ok=True)
    written = [research / "results" / "SCOREBOARD.md", research / "results" / "dashboard.json"]
    written[0].write_text(render(rows, qualifications))
    written[1].write_text(json.dumps(dashboard, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    for folder in sorted((research / "capabilities").glob("C*-*")):
        path = folder / "HISTORY.md"
        path.write_text(history(rows, folder.name.split("-")[0], qualifications))
        written.append(path)
    return written


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) > 1:
        sys.exit("Usage: python -m questionize.scoreboard [ledger.jsonl]")
    ledger = Path(args[0]) if args else LEDGER
    if not ledger.is_file():
        sys.exit(f"Ledger not found: {ledger}; reports were not changed.")
    for path in write_all(load(ledger)):
        print(path)


if __name__ == "__main__":
    main()
