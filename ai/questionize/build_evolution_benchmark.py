"""Project an existing private E1 baseline into an abstract decision-replay benchmark.

    python -m questionize.build_evolution_benchmark DATASET BASELINE_RUN --out PRIVATE_FILE

Only hashed case IDs, subtype/operator, answer letters and Judge first-rate leave the source
dataset. It excludes every flagged capture and the entire formatting-dependent structure type.
The source remains unchanged. The output must stay outside this public repository.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .evolution import Benchmark, ReplayCase, case_decision, content_hash
from .operator_policy import task_operator

REPO = Path(__file__).resolve().parents[2]


def build(dataset: dict, outcomes: list[dict], dataset_hash: str, source_run: str) -> dict:
    by_id = {row["entry_id"]: row for row in outcomes if row.get("condition") == "B1"}
    cases, excluded = [], {"flagged": 0, "structure": 0, "not_test": 0, "missing_baseline": 0, "unverified_key": 0}
    for item in dataset["items"]:
        if item.get("flagged"):
            excluded["flagged"] += 1
            continue
        if item.get("subtype") == "structure":
            excluded["structure"] += 1
            continue
        if item.get("split") != "test":
            excluded["not_test"] += 1
            continue
        if item.get("key_verdict") not in ("book", "agrees", "upheld") or not item.get("answer_key"):
            excluded["unverified_key"] += 1
            continue
        row = by_id.get(item["entry_id"])
        if row is None:
            excluded["missing_baseline"] += 1
            continue
        if row.get("key") != item.get("answer_key"):
            raise ValueError("recorded answer key does not match the dataset")
        notes = row.get("notes", {})
        case = ReplayCase(
            case_id=hashlib.sha256(f"{dataset_hash}:{item['entry_id']}".encode()).hexdigest()[:24],
            subtype=item.get("subtype") or "unknown", operator=task_operator(item["question"]["stem"]),
            solver_answer=notes["solver"], judge_answer=notes.get("judge_top"),
            judge_first_rate=notes.get("judge_first_rate"), key=item["answer_key"], baseline_answer=row["answer"],
        )
        if case_decision(case, None)["chosen_answer"] != case.baseline_answer:
            raise ValueError("legacy replay does not reproduce the recorded baseline")
        cases.append(case.model_dump())
    if not cases or excluded["missing_baseline"]:
        raise ValueError("all eligible test cases need a baseline result")
    benchmark = Benchmark(id="official-cr-v1-decision-replay-v1", hash=content_hash(cases), kind="decision_replay", cases=cases)
    return {
        **benchmark.model_dump(), "subject": "CR", "level": "gmat", "capability": "C3.1",
        "evidence_scope": "development_regression", "parent_dataset_hash": dataset_hash,
        "parent_dataset_id": dataset.get("dataset", "unknown"), "source_run": source_run,
        "excluded": excluded, "n_cases": len(cases),
        "observations": {
            "recorded_cases": len(cases),
            "except_cases": sum(case["operator"] == "except" for case in cases),
            "except_wrong_overrides": sum(case["operator"] == "except" and case["solver_answer"] == case["key"] and case["baseline_answer"] != case["key"] for case in cases),
            "standard_wrong_overrides": sum(case["operator"] == "standard" and case["solver_answer"] == case["key"] and case["baseline_answer"] != case["key"] for case in cases),
        },
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.resolve().is_relative_to(REPO):
        parser.error("The private benchmark must be written outside the public repository")
    raw = args.dataset.read_bytes()
    dataset_hash = hashlib.sha256(raw).hexdigest()[:16]
    manifest = json.loads((args.baseline / "manifest.json").read_text())
    if manifest.get("dataset_hash") != dataset_hash:
        parser.error("Baseline and dataset hashes do not match")
    outcomes = [json.loads(line) for line in (args.baseline / "results.jsonl").read_text().splitlines() if line.strip()]
    result = build(json.loads(raw), outcomes, dataset_hash, manifest["run_id"])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    args.out.chmod(0o600)
    print(json.dumps({"benchmark_id": result["id"], "hash": result["hash"], "n_cases": result["n_cases"], "observations": result["observations"]}))


if __name__ == "__main__":
    main()
