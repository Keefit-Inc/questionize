"""Apply a private, source-reviewed repair manifest without overwriting an OG dataset.

python -m questionize.capture_audit INPUT --repairs PRIVATE_JSON --out PRIVATE_OUTPUT
The manifest is evidence supplied by the reviewer, not a second AI vote.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def issues(item: dict) -> list[str]:
    q = item.get("question", {})
    choices = q.get("choices", [])
    found = []
    if [c.get("label") for c in choices] != list("ABCDE"):
        found.append("invalid_choices")
    if item.get("answer_key") not in list("ABCDE"):
        found.append("invalid_key")
    if any(not q.get(k, "").strip() for k in ("passage", "stem")):
        found.append("missing_text")
    if not item.get("number"):
        found.append("missing_printed_number")
    if "bold" in q.get("stem", "").lower() and not re.search(r"\[BOLD_\d+\].+?\[/BOLD_\d+\]", q.get("passage", ""), re.S):
        found.append("missing_required_emphasis")
    return found


def repair(data: dict, manifest: dict) -> tuple[dict, dict]:
    data = json.loads(json.dumps(data))
    applied = []
    patches = {p["entry_id"]: p for p in manifest["patches"]}
    for item in data["items"]:
        patch = patches.get(item["entry_id"])
        if not patch:
            continue
        if not patch.get("reviewed_against_scan"):
            raise ValueError("Every repair requires a recorded source inspection")
        if "number" in patch:
            item["number"] = patch["number"]
        if "subtype" in patch:
            item["subtype"] = patch["subtype"]
        if "question_patch" in patch:
            if set(patch["question_patch"]) - {"passage", "stem", "choices"}:
                raise ValueError("Unsupported question field")
            item["question"].update(patch["question_patch"])
        for field in ("official_explanation", "option_explanations"):
            if field in patch:
                item[field] = patch[field]
        for n, span in reversed(list(enumerate(patch.get("bold_spans", []), 1))):
            passage = item["question"]["passage"]
            if passage.count(span) != 1:
                raise ValueError(f"Repair {item['entry_id']} span is not unique in source transcription")
            item["question"]["passage"] = passage.replace(span, f"[BOLD_{n}]{span}[/BOLD_{n}]")
        item["capture_review"] = {"method": "agent_visual_source_inspection", "pdf_page": item["page"],
                                  "fields": sorted(k for k in patch if k not in ("entry_id", "reviewed_against_scan"))}
        applied.append(item["entry_id"])
    if set(patches) != set(applied):
        raise ValueError("Unknown correction IDs")
    data["dataset"] = manifest.get("output_dataset", "official-cr-v2")
    data["capture_provenance"] = {"parent_dataset": manifest["parent_dataset"], "parent_hash": manifest["parent_hash"],
        "pdf_hash": manifest["pdf_hash"], "namespace": "expert_reference", "rights_scope": "private_research",
        "reviewer": "AI agent visual inspection; not an independent human certification",
        "expert_explanations": "reference text retained privately; no AI text replaces it",
        "derived_memory_namespace": "ai_derived_from_expert_reference", "repaired_at": datetime.now(timezone.utc).isoformat()}
    summary = {"total": len(data["items"]), "eligible": sum(not i.get("flagged") for i in data["items"]),
               "held_flagged": sum(bool(i.get("flagged")) for i in data["items"]), "repaired_items": len(applied),
               "restored_emphasis_items": sum(bool(p.get("bold_spans")) for p in patches.values()),
               "restored_identifiers": sum("number" in p for p in patches.values()),
               "mechanical_issues": {str(i["entry_id"]): issues(i) for i in data["items"] if issues(i)},
               "visual_review_scope": "correction fields only; not every character of every page",
               "independent_human_review": False}
    return data, summary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", type=Path)
    p.add_argument("--repairs", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    from .import_scan import inside_repo
    if inside_repo(args.out) or args.out.exists():
        raise SystemExit("Use a new private output outside the public repository")
    manifest = json.loads(args.repairs.read_text())
    if manifest["parent_hash"] != digest(args.input):
        raise SystemExit("Parent hash mismatch")
    data, summary = repair(json.loads(args.input.read_text()), manifest)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    args.out.chmod(0o600)
    summary.update(dataset_hash=digest(args.out), manifest_hash=digest(args.repairs), parent_hash=manifest["parent_hash"],
                   pdf_hash=manifest["pdf_hash"])
    audit = args.out.with_suffix(".audit.json")
    audit.write_text(json.dumps(summary, indent=2) + "\n")
    audit.chmod(0o600)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
