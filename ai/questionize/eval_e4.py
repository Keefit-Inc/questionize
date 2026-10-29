"""E4: capture fidelity, and the verified, split dataset that E1 and the memory use.

    python -m questionize.eval_e4 ~/private/og-rules.json ~/private/og-model.json --out ~/private/official-cr-v1.json

Two independent captures of the same pages, layout rules (R) and the model structuring OCR text (M-text),
are matched by the page each question starts on and compared field by field. Where they agree on every field and the key,
the item is taken as verified; where they disagree it is flagged for a person to check against the page
(research/protocols/E4-capture.md). Until a person has checked a sample, agreement between R and M is
reported as agreement, not accuracy.

Verified items are split deterministically into train (60%) and test (40%) by a hash of the dataset id
and question number, so the memory is learned on items E1 never scores.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from .eval_e1 import git_sha, wilson

PROTOCOL, PROTOCOL_VERSION, CAPABILITIES = "E4", 1, ["C1.1"]
SAME = 0.98
TEST_SHARE = 0.4
FIELDS = ("passage", "stem", "A", "B", "C", "D", "E")


def words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.replace("’", "'").lower())


def similarity(a: str, b: str) -> float:
    wa, wb = words(a), words(b)
    if not wa and not wb:
        return 1.0
    return difflib.SequenceMatcher(None, wa, wb, autojunk=False).ratio()


def fields(item: dict) -> dict[str, str]:
    q = item["question"]
    out = {"passage": q["passage"], "stem": q["stem"]}
    out.update({c["label"]: c["text"] for c in q["choices"]})
    return out


def split_of(dataset: str, number: str) -> str:
    h = int(hashlib.sha256(f"{dataset}:{number}".encode()).hexdigest(), 16)
    return "test" if (h % 1000) / 1000 < TEST_SHARE else "train"


def compare(rules: list[dict], model: list[dict], dataset: str) -> tuple[list[dict], dict]:
    # Both captures record the page a question starts on; numbers can be missing where OCR dropped them.
    by_page = {i["page"]: i for i in rules}
    merged, field_same = [], {f: 0 for f in (*FIELDS, "key")}
    matched = agreed = 0
    for m in model:
        r = by_page.get(m.get("page"))
        if r is None:
            merged.append(m | {"flags": [*m.get("flags", []), "no_rules_match"], "flagged": True})
            continue
        matched += 1
        fr, fm = fields(r), fields(m)
        differs = [f for f in FIELDS if similarity(fr.get(f, ""), fm.get(f, "")) < SAME]
        for f in FIELDS:
            field_same[f] += f not in differs
        key_same = r.get("answer_key") == m.get("answer_key")
        field_same["key"] += key_same
        flags = [*m.get("flags", []), *r.get("flags", [])]
        if differs:
            flags.append("rules_vs_model:" + ",".join(differs))
        if not key_same:
            flags.append("rules_vs_model:key")
        ok = not flags
        agreed += ok
        # The model's capture carries the explanation split by option and the trap tags; keep it.
        number = m.get("number") or r.get("number", "")
        merged.append(m | {"number": number, "flags": flags, "flagged": not ok, "split": split_of(dataset, number or m["page"]) if ok else ""})
    n = max(matched, 1)
    summary = {
        "R_vs_Mtext": {"primary": round(agreed / n, 4), "ci95": wilson(agreed, matched), "n": matched},
        "field_agreement": {f: round(c / n, 4) for f, c in field_same.items()},
        "counts": {"rules": len(rules), "model": len(model), "matched": matched, "agreed": agreed,
                   "train": sum(i.get("split") == "train" for i in merged), "test": sum(i.get("split") == "test" for i in merged)},
    }
    return merged, summary


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rules", type=Path)
    ap.add_argument("model", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--ledger", type=Path, default=Path(__file__).resolve().parents[2] / "research" / "ledger.jsonl")
    args = ap.parse_args(argv)
    if args.out.resolve().is_relative_to(Path(__file__).resolve().parents[2]):
        sys.exit("Refusing to write book text inside the repository; choose a path outside it.")

    rules, model = json.loads(args.rules.read_text()), json.loads(args.model.read_text())
    dataset = model.get("dataset", "official-cr-v1")
    merged, summary = compare(rules["items"], model["items"], dataset)
    out = {"dataset": dataset, "source": "scan+R+Mtext", "exported_at": datetime.now(timezone.utc).isoformat(), "items": merged}
    args.out.write_text(json.dumps(out, indent=1, ensure_ascii=False))

    started = datetime.now(timezone.utc)
    line = {
        "run_id": started.strftime("%Y%m%dT%H%M%SZ") + "-e4", "protocol": PROTOCOL, "protocol_version": PROTOCOL_VERSION,
        "capabilities": CAPABILITIES, "started_at": started.isoformat(), "git_sha": git_sha(),
        "models": {"structurer": model.get("model", "")}, "dataset_id": dataset,
        "dataset_hash": hashlib.sha256(args.out.read_bytes()).hexdigest()[:16], "n_items": len(merged),
        "reference": "agreement between layout rules and model structuring; no human check yet",
        "subject": "CR",
        "summary": summary,
    }
    with args.ledger.open("a") as f:
        f.write(json.dumps(line) + "\n")
    print(json.dumps(summary, indent=1))
    for i in merged:
        if i["flagged"]:
            print(f"  check page {i.get('page')} #{i.get('number')}: {', '.join(i['flags'])}")
    print(f"→ {args.out}; ledger line appended to {args.ledger}")


if __name__ == "__main__":
    main()
