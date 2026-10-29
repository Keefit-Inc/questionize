"""Turn the experiment ledger into a scoreboard: the latest result for each capability against its bar.

    python -m questionize.scoreboard [../research/ledger.jsonl] > ../research/results/SCOREBOARD.md

The capabilities, their primary measures and bars are those in research/README.md. A run marked
invalidated by a later ledger line is left out.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

LEDGER = Path(__file__).resolve().parents[2] / "research" / "ledger.jsonl"

CAPABILITIES: list[tuple[str, str, str]] = [
    ("C1.1", "Capture: extract", "items with every role right ≥ 98%; CER ≤ 1% scans, ≤ 2% photos"),
    ("C1.2", "Capture: reconstruct", "solvability equivalence ≥ 95% on items with figures"),
    ("C2", "Understand the item", "skill agreement ≥ 90%; trap tags ≥ 80%; difficulty ρ ≥ 0.4"),
    ("C3.1", "Solve", "accuracy against the key ≥ 95% (CR)"),
    ("C3.2", "Explain", "explanations rated correct ≥ 90%"),
    ("C3.3", "Explain at the learner's level", "readability in band ≥ 90%; preferred to generic"),
    ("C4", "Diagnose the learner", "misconception top-3 ≥ 70%; next-miss AUC ≥ 0.65"),
    ("C5", "Write practice", "first-draft verification rate rising with memory; two-answer rate ≤ 2%"),
    ("C6", "Choose practice", "success on recommended 60%–80%; gains over unrecommended"),
]


def load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    invalid = {r["invalidates"] for r in rows if r.get("invalidates")}
    return [r for r in rows if r.get("run_id") and r["run_id"] not in invalid and not r.get("invalidates")]


def headline(summary: dict) -> str:
    """'B0 0.82 [0.71, 0.89] · B1 …' from a per-condition summary with accuracy or a named primary measure."""
    parts = []
    for cond, m in summary.items():
        if not isinstance(m, dict):
            continue
        value = m.get("primary", m.get("accuracy"))
        if value is None:
            continue
        ci = m.get("ci95")
        parts.append(f"{cond} {value:.2f}" + (f" [{ci[0]:.2f}, {ci[1]:.2f}]" if ci else "") + f" (n={m.get('n', '?')})")
    return " · ".join(parts) or "see run"


def render(rows: list[dict]) -> str:
    out = [
        "# Scoreboard",
        "",
        (
            "Generated from `research/ledger.jsonl` by `python -m questionize.scoreboard`; do not edit by hand. "
            "Latest valid run per capability; bars from research/README.md."
        ),
        "",
        "| Capability | Bar | Latest result | Run |",
        "|---|---|---|---|",
    ]
    for cap, name, bar in CAPABILITIES:
        runs = [r for r in rows if cap in r.get("capabilities", [])]
        if runs:
            r = max(runs, key=lambda r: r.get("started_at", ""))
            result = headline(r.get("summary", {}))
            run = f"{r['protocol']} v{r.get('protocol_version', 1)} · {r['run_id']} · {', '.join(r.get('models', {}).values())}"
        else:
            result, run = "not measured yet", ""
        out.append(f"| {cap} {name} | {bar} | {result} | {run} |")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[1:]
    print(render(load(Path(args[0]) if args else LEDGER)), end="")


if __name__ == "__main__":
    main()
