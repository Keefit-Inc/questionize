"""Append the service's aggregate E8 records to the existing research ledger.

This reads a public aggregate feed, never private replay cases or account tokens.
Run scoreboard afterwards to reproduce the Markdown and JSON projections.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .scoreboard import LEDGER


def append_records(path: Path, rows: list[dict]) -> int:
    existing = {row["run_id"]: row for line in path.read_text().splitlines() if line.strip()
                for row in [json.loads(line)] if row.get("run_id")} if path.exists() else {}
    pending = []
    for row in rows:
        e8 = row.get("protocol") == "E8" and row.get("evaluation_scope") == "regression" and str(row.get("run_id", "")).startswith("cycle-")
        e11 = row.get("protocol") == "E11" and row.get("evaluation_scope") == "trial" and str(row.get("run_id", "")).startswith("memory-cycle-")
        if not (e8 or e11):
            raise ValueError("Only aggregate E8 regression or E11 local-pilot cycle records are accepted")
        if row["run_id"] in existing:
            if existing[row["run_id"]] != row:
                raise ValueError(f"Published cycle changed after recording: {row['run_id']}")
            continue
        existing[row["run_id"]] = row
        pending.append(row)
    if pending:
        path.parent.mkdir(parents=True, exist_ok=True)
        prefix = "\n" if path.exists() and path.stat().st_size and not path.read_bytes().endswith(b"\n") else ""
        with path.open("a") as stream:
            stream.write(prefix)
            for row in pending:
                stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return len(pending)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="https://questionize.org/admin/cycles/ledger")
    parser.add_argument("--ledger", type=Path, default=LEDGER)
    args = parser.parse_args()
    parsed = urlparse(args.url)
    if parsed.scheme != "https" and not (parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1"}):
        parser.error("Use HTTPS, or localhost for an offline development service")
    with urlopen(Request(args.url, headers={"Accept": "application/x-ndjson", "Cache-Control": "no-cache"}), timeout=20) as response:
        raw = response.read(1_000_001)
    if len(raw) > 1_000_000:
        parser.error("Aggregate feed exceeded the size limit")
    rows = [json.loads(line) for line in raw.decode().splitlines() if line.strip()]
    print(f"Appended {append_records(args.ledger, rows)} new E8/E11 records; previous ledger lines were preserved.")


if __name__ == "__main__":
    main()
