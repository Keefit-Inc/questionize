"""Cross-check private OCR caches. Disagreement is a review signal, never a gold label.

python -m questionize.source_crosscheck DATASET --cache PRIVATE_CACHE --out PRIVATE_REPORT
The cache has ocr/<page>.json (Apple Vision lines) and tesseract/<page>.txt.
"""
import argparse
import difflib
import hashlib
import json
import re
from pathlib import Path


def tokens(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def missing_segments(reference, extracted):
    a, b = tokens(reference), tokens(extracted)
    normalized = " ".join(b)
    return [" ".join(a[x:y]) for op, x, y, _, _ in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
            if op == "delete" and y - x >= 2 and " ".join(a[x:y]) not in normalized]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("dataset", type=Path)
    p.add_argument("--cache", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    from .import_scan import inside_repo
    if inside_repo(args.out) or args.out.exists():
        raise SystemExit("Use a new private report path")
    data = json.loads(args.dataset.read_text())
    rows = []
    for item in data["items"]:
        page = str(item["page"])
        source = (args.cache / "tesseract" / f"{page}.txt").read_text()
        apple_path = args.cache / "ocr" / f"{page}.json"
        key = re.search(r"The correct answer is\s+([A-E])", source, re.I)
        a_label = re.search(r"\(A\)", source)
        captured = re.sub(r"\[/?BOLD_\d+\]", "", item["question"]["passage"] + " " + item["question"]["stem"])
        reference = source[:a_label.start()] if a_label else ""
        a, b = tokens(reference), tokens(captured)
        start = next((j for j in range(len(a)) if a[j:j+4] == b[:4]), None)
        omissions = missing_segments(" ".join(a[start:]), captured) if start is not None else None
        rows.append({"entry_id": item["entry_id"], "split": item.get("split"), "key_matches": bool(key and key.group(1).upper() == item["answer_key"]),
            "stimulus_aligned": start is not None, "possible_omissions": omissions,
            "tesseract_hash": hashlib.sha256(source.encode()).hexdigest(), "apple_hash": hashlib.sha256(apple_path.read_bytes()).hexdigest()})
    report = {"dataset_hash": hashlib.sha256(args.dataset.read_bytes()).hexdigest(), "summary": {
        "items": len(rows), "keys_independently_read": sum(r["key_matches"] for r in rows),
        "stimulus_regions_aligned": sum(r["stimulus_aligned"] for r in rows),
        "possible_omission_items": sum(bool(r["possible_omissions"]) for r in rows),
        "unmatched_regions_for_review": sum(not r["stimulus_aligned"] for r in rows)}, "private_rows": rows}
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    args.out.chmod(0o600)
    print(json.dumps(report["summary"]))


if __name__ == "__main__":
    main()
