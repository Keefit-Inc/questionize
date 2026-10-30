"""Publish only aggregate E9/E10 evidence from private run directories."""
import argparse
import json
from pathlib import Path

from .research_map import project_registry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", type=Path, nargs="+")
    args = parser.parse_args()
    research = Path(__file__).resolve().parents[2] / "research"
    target = research / "evidence-map.json"
    registry = json.loads(target.read_text())
    for path in args.runs:
        manifest = json.loads((path / "manifest.json").read_text())
        summary = json.loads((path / "summary.json").read_text())
        protocol = manifest["protocol"]
        if protocol not in ("E9", "E10") or manifest["evaluation_scope"] != "full":
            raise SystemExit("Publish completed full E9/E10 runs, not selected smoke results")
        limitations = "Known development set; targeted agent visual repairs, no independent human capture certification. Same-model Judge, no human explanation ratings; no 99.9% claim."
        decision = "Research observation only; no new semantic-policy adoption."
        if protocol == "E10":
            controls = summary["by_type"].get("valid_control", {})
            gate = (summary["parents"] == 8 and summary["expected"] == 34 and controls.get("n") == 8
                    and summary["guarded"]["n"] == 26 and summary["errors"] == 0
                    and summary["completed"] == summary["expected"] and summary["guarded"]["false_accepts"] == 0
                    and controls.get("guarded_accepted") == controls.get("legacy_accepted"))
            decision = "Integrity guard eligible for release under E10 contracts." if gate else "Hold broader release claims: defect or execution failures remain."
            limitations = "Constructed defects from eight shared parents, not independent population samples. Exact duplicate, wrong-key, explicit contradiction and missing-format contracts do not certify subtle ambiguity or learner benefit."
        entry = {"run_id": manifest["run_id"], "protocol": protocol, "scope": "development evaluation", "limitations": limitations,
                 "decision": decision, "report_path": f"research/results/{protocol}.md", "summary": summary}
        safe = project_registry({"schema_version": 1, "evaluations": [entry]}, [])["evaluations"][0]
        registry["evaluations"] = [e for e in registry["evaluations"] if e["protocol"] != protocol] + [safe]
    target.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n")
    print("Published aggregate evidence for", ", ".join(e["protocol"] for e in registry["evaluations"]))


if __name__ == "__main__":
    main()
