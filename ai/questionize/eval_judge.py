"""Score the Argument Judge against a human-adjudicated gold set.

    python -m questionize.eval_judge eval/gold.jsonl [--out eval/report.json]

Each line of the gold file is one item: passage, stem, choices (A-E), subtype and the
adjudicated `gold_label`. The judge never sees the gold label when it rates options; the
label is only used afterwards to score it. Reports accuracy, how often items clear the gate,
and calibration (expected calibration error of the judge's confidence in its top option).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
from pathlib import Path

from pydantic import BaseModel

from .judge import SUBTYPE_MEASURES, ArgumentJudge
from .schemas import Choice, JudgeRequest, JudgeResult, Label


class GoldItem(BaseModel):
    id: str
    passage: str
    stem: str
    choices: list[Choice]
    subtype: str
    gold_label: Label
    adjudicator: str = ""
    notes: str = ""


def top_option(result: JudgeResult) -> Label:
    index = 0 if result.measure == "support_delta" else 1
    sign = 1.0 if result.direction == "max" else -1.0
    return max(result.options, key=lambda o: sign * (o.support_delta, o.necessity)[index].value).label


def expected_calibration_error(pairs: list[tuple[float, bool]], bins: int = 5) -> float:
    if not pairs:
        return 0.0
    total, error = len(pairs), 0.0
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        bucket = [(c, ok) for c, ok in pairs if lo <= c < hi or (b == bins - 1 and c == 1.0)]
        if bucket:
            confidence = statistics.fmean(c for c, _ in bucket)
            accuracy = statistics.fmean(1.0 if ok else 0.0 for _, ok in bucket)
            error += len(bucket) / total * abs(confidence - accuracy)
    return error


async def evaluate(judge: ArgumentJudge, items: list[GoldItem]) -> dict:
    rows, pairs = [], []
    for item in items:
        if item.subtype not in SUBTYPE_MEASURES:
            rows.append({"id": item.id, "subtype": item.subtype, "skipped": "sub-type not covered by the judge yet"})
            continue
        request = JudgeRequest(
            passage=item.passage, stem=item.stem, choices=item.choices, correct_label=item.gold_label, subtype=item.subtype
        )
        result = await judge.judge(request)
        predicted = top_option(result)
        correct = predicted == item.gold_label
        # Confidence in the judge's own top choice: the share of resamples where the gold key leads,
        # or what is left of it when the judge prefers another option.
        confidence = result.key_first_rate if correct else 1.0 - result.key_first_rate
        pairs.append((confidence, correct))
        rows.append(
            {
                "id": item.id, "subtype": item.subtype, "gold": item.gold_label, "predicted": predicted,
                "correct": correct, "verdict": result.verdict, "margin": result.margin,
                "key_first_rate": result.key_first_rate, "confidence": round(confidence, 3),
            }
        )

    scored = [r for r in rows if "correct" in r]
    return {
        "judge_version": judge.version,
        "items": len(items),
        "scored": len(scored),
        "accuracy": round(statistics.fmean(r["correct"] for r in scored), 3) if scored else None,
        "gate_pass_rate": round(statistics.fmean(r["verdict"] == "pass" for r in scored), 3) if scored else None,
        "mean_margin": round(statistics.fmean(r["margin"] for r in scored), 3) if scored else None,
        "ece": round(expected_calibration_error(pairs), 3),
        "rows": rows,
    }


def load_gold(path: Path) -> list[GoldItem]:
    return [GoldItem.model_validate_json(line) for line in path.read_text().splitlines() if line.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("gold", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    from .app import build_judge
    from .config import load_settings
    from .llm import make_llm

    settings = load_settings()
    primary = make_llm(settings.primary, timeout=settings.timeout_seconds)
    solver = primary if settings.solver == settings.primary else make_llm(settings.solver, timeout=settings.timeout_seconds)
    report = asyncio.run(evaluate(build_judge(settings, primary, solver), load_gold(args.gold)))

    text = json.dumps(report, indent=2)
    if args.out:
        args.out.write_text(text + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
