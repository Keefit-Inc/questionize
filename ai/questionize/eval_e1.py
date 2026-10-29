"""E1: solving and explaining official-style items (research/protocols/E1-solve-and-explain.md).

    python -m questionize.eval_e1 ~/private/official-cr-v1.json --conditions B0,B1,B2 \\
        [--limit 80] [--out ~/questionize-research/runs] [--ledger ../research/ledger.jsonl]

The dataset is a curator's export from the web app (Me → Research dataset): item text from their
device plus the book's answer key. It is private and is read from outside the repository; this script
writes its run directory outside the repository too, and appends only aggregate numbers to the ledger.

Conditions:
  B0  one model answers and explains in one call;
  B1  a blind solver answers, the Argument Judge measures the options where it covers the sub-type and
      overrides the solver only when its ranking is stable, then the answer is explained;
  B2  two models answer independently, read each other's reasoning, answer again, and the settled
      answer is explained (B2' when both "models" are the same one, reported as such).
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import math
import random
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .eval_judge import expected_calibration_error
from .judge import SUBTYPE_MEASURES, ArgumentJudge, rank
from .llm import StructuredLLM
from .schemas import Label, SolverResult

PROTOCOL, PROTOCOL_VERSION = "E1", 2
CAPABILITIES = ["C3.1", "C3.2"]
ROOT = Path(__file__).resolve().parent
JUDGE_OVERRIDE_RATE = 0.8
DEBATE_ROUNDS = 2  # exchanges after the independent answers
BOOTSTRAP_ROUNDS = 2000

B0_SYSTEM = """You are an expert GMAT/LSAT tutor. Answer the multiple-choice question, then explain to a \
student why the answer is right and why each other option is wrong. Be accurate above all."""

EXPLAIN_SYSTEM = """You are an expert GMAT/LSAT tutor. The answer to this question has been settled. Explain \
to a student why it is right and why each other option is wrong, in under 150 words. Be accurate above all; \
if the settled answer looks wrong to you, say so plainly instead of defending it."""

DEBATE_SYSTEM = """You are an expert GMAT/LSAT test-taker. Another expert answered the same question; their \
reasoning is below. Reconsider carefully, then give your final answer. Change your answer only if their \
reasoning shows yours is wrong."""


class AnswerAndExplanation(BaseModel):
    answer_label: Label
    confidence: float = Field(..., ge=0, le=1)
    explanation: str


class Explanation(BaseModel):
    explanation: str
    disagrees_with_settled_answer: bool = False


class DatasetQuestion(BaseModel):
    passage: str
    stem: str
    choices: list[dict[str, str]]


class DatasetItem(BaseModel):
    entry_id: int
    answer_key: Label | None = None
    key_verdict: str = "unchecked"
    subtype: str = ""
    question: DatasetQuestion
    official_explanation: str = ""
    flagged: bool = False
    split: str = ""


@dataclass
class Outcome:
    entry_id: int
    condition: str
    answer: str
    key: str
    confidence: float | None
    explanation: str
    calls: int
    notes: dict[str, Any] = field(default_factory=dict)

    @property
    def correct(self) -> bool:
        return self.answer == self.key


def item_text(q: DatasetQuestion) -> str:
    options = "\n".join(f"({c['label']}) {c['text']}" for c in q.choices)
    return f"PASSAGE:\n{q.passage}\n\nQUESTION:\n{q.stem}\n\nOPTIONS:\n{options}"


async def run_b0(primary: StructuredLLM, item: DatasetItem) -> Outcome:
    r = await primary.complete(B0_SYSTEM, item_text(item.question), AnswerAndExplanation, temperature=0.0)
    return Outcome(item.entry_id, "B0", r.answer_label, item.answer_key or "", r.confidence, r.explanation, 1)


async def explain(primary: StructuredLLM, item: DatasetItem, answer: str) -> tuple[str, bool]:
    r = await primary.complete(EXPLAIN_SYSTEM, f"{item_text(item.question)}\n\nSETTLED ANSWER: {answer}", Explanation, temperature=0.0)
    return r.explanation, r.disagrees_with_settled_answer


async def run_b1(primary: StructuredLLM, solver: StructuredLLM, judge: ArgumentJudge | None, item: DatasetItem, rng: random.Random) -> Outcome:
    solved = await solver.complete("You are an expert GMAT/LSAT test-taker. Solve the question; report your honest confidence.",
                                   item_text(item.question), SolverResult, temperature=0.0)
    answer, calls, notes = solved.answer_label, 1, {"solver": solved.answer_label}
    measure, direction = SUBTYPE_MEASURES.get(item.subtype, (None, None))
    if judge is not None and measure:
        options = [(c["label"], c["text"]) for c in item.question.choices]
        samples = await judge.sample(item.question.passage, item.question.stem, options)
        calls += len(samples)
        best, first_rate, margin, _ = rank(samples, measure, direction, rng)
        notes.update(judge_top=best, judge_first_rate=round(first_rate, 3), judge_margin=round(margin, 3))
        if best != answer and first_rate >= JUDGE_OVERRIDE_RATE:
            answer = best
            notes["judge_override"] = True
    text, disagrees = await explain(primary, item, answer)
    notes["explainer_disagrees"] = disagrees
    return Outcome(item.entry_id, "B1", answer, item.answer_key or "", solved.confidence, text, calls + 1, notes)


async def run_b2(a: StructuredLLM, b: StructuredLLM, item: DatasetItem, label: str) -> Outcome:
    text = item_text(item.question)
    solve = "You are an expert GMAT/LSAT test-taker. Solve the question; report your honest confidence."
    first_a, first_b = await asyncio.gather(
        a.complete(solve, text, SolverResult, temperature=0.0), b.complete(solve, text, SolverResult, temperature=0.0)
    )
    calls, notes = 2, {"round1": [first_a.answer_label, first_b.answer_label]}
    final_a, final_b = first_a, first_b
    for rnd in range(2, 2 + DEBATE_ROUNDS):
        if final_a.answer_label == final_b.answer_label:
            break
        final_a, final_b = await asyncio.gather(
            a.complete(DEBATE_SYSTEM, f"{text}\n\nOTHER EXPERT ANSWERED {final_b.answer_label}:\n{final_b.reasoning}", SolverResult, temperature=0.0),
            b.complete(DEBATE_SYSTEM, f"{text}\n\nOTHER EXPERT ANSWERED {final_a.answer_label}:\n{final_a.reasoning}", SolverResult, temperature=0.0),
        )
        calls += 2
        notes[f"round{rnd}"] = [final_a.answer_label, final_b.answer_label]
    # Settled when both agree; otherwise the more confident final answer stands.
    settled = final_a if final_a.answer_label == final_b.answer_label or final_a.confidence >= final_b.confidence else final_b
    notes["agreed"] = final_a.answer_label == final_b.answer_label
    explanation, disagrees = await explain(a, item, settled.answer_label)
    notes["explainer_disagrees"] = disagrees
    return Outcome(item.entry_id, label, settled.answer_label, item.answer_key or "", settled.confidence, explanation, calls + 1, notes)


# ------------------------------------------------------------------ statistics


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (round(centre - half, 4), round(centre + half, 4))


def mcnemar(base: dict[int, bool], other: dict[int, bool]) -> dict[str, Any]:
    """Exact two-sided McNemar test on paired outcomes: b = base wrong & other right, c = the reverse."""
    shared = base.keys() & other.keys()
    b = sum(1 for i in shared if not base[i] and other[i])
    c = sum(1 for i in shared if base[i] and not other[i])
    n = b + c
    tail = sum(math.comb(n, k) for k in range(min(b, c) + 1)) / (2**n) if n else 1.0
    return {"b": b, "c": c, "p": round(min(1.0, 2 * tail), 4)}


def paired_diff_ci(base: dict[int, bool], other: dict[int, bool], rng: random.Random) -> tuple[float, float]:
    """Paired bootstrap 95% interval for accuracy(other) - accuracy(base) over the items both answered."""
    shared = sorted(base.keys() & other.keys())
    if not shared:
        return (0.0, 0.0)
    diffs = [int(other[i]) - int(base[i]) for i in shared]
    means = sorted(sum(rng.choice(diffs) for _ in diffs) / len(diffs) for _ in range(BOOTSTRAP_ROUNDS))
    return (round(means[int(0.025 * BOOTSTRAP_ROUNDS)], 4), round(means[int(0.975 * BOOTSTRAP_ROUNDS) - 1], 4))


def load_baseline(run_dir: Path) -> dict[str, dict[int, bool]]:
    """Per-condition correctness from an earlier run's results.jsonl, to pair against."""
    out: dict[str, dict[int, bool]] = {}
    for line in (run_dir / "results.jsonl").read_text().splitlines():
        r = json.loads(line)
        out.setdefault(r["condition"], {})[r["entry_id"]] = r["correct"]
    return out


def summarize(outcomes: list[Outcome], seed: int = 7, baseline: dict[str, dict[int, bool]] | None = None) -> dict[str, Any]:
    by: dict[str, dict[int, Outcome]] = {}
    for o in outcomes:
        by.setdefault(o.condition, {})[o.entry_id] = o
    summary: dict[str, Any] = {}
    base = {i: o.correct for i, o in by.get("B0", {}).items()}
    for cond, rows in sorted(by.items()):
        k, n = sum(o.correct for o in rows.values()), len(rows)
        stated = [(o.confidence, o.correct) for o in rows.values() if o.confidence is not None]
        entry: dict[str, Any] = {
            "n": n,
            "accuracy": round(k / n, 4) if n else None,
            "ci95": wilson(k, n),
            "ece": round(expected_calibration_error(stated), 4) if stated else None,
            "calls": sum(o.calls for o in rows.values()),
        }
        if cond != "B0" and base:
            paired = {i: o.correct for i, o in rows.items()}
            entry["vs_B0"] = mcnemar(base, paired) | {"diff_ci95": paired_diff_ci(base, paired, random.Random(seed))}
        before = (baseline or {}).get(cond.removesuffix("+M"))
        if before and cond.endswith("+M"):
            paired = {i: o.correct for i, o in rows.items()}
            k0 = sum(before[i] for i in paired if i in before)
            entry["vs_baseline"] = mcnemar(before, paired) | {
                "baseline_accuracy": round(k0 / max(1, len(paired.keys() & before.keys())), 4),
                "diff_ci95": paired_diff_ci(before, paired, random.Random(seed)),
            }
        summary[cond] = entry
    return summary


# ------------------------------------------------------------------ run bookkeeping


def prompts_hash() -> str:
    h = hashlib.sha256()
    for name in ("prompts.py", "levels.py", "judge.py", "eval_e1.py", "import_scan.py"):
        h.update((ROOT / name).read_bytes())
    return h.hexdigest()[:16]


def git_sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def load_dataset(path: Path) -> tuple[str, str, list[DatasetItem], dict[str, int]]:
    raw = path.read_bytes()
    data = json.loads(raw)
    items = [DatasetItem.model_validate(i) for i in data.get("items", [])]
    usable = [i for i in items if i.answer_key and i.key_verdict != "disputed" and not i.flagged]
    excluded = {
        "no_key": sum(1 for i in items if not i.answer_key),
        "disputed_key": sum(1 for i in items if i.answer_key and i.key_verdict == "disputed"),
        "flagged_scan": sum(1 for i in items if i.answer_key and i.key_verdict != "disputed" and i.flagged),
    }
    return data.get("dataset", path.stem), hashlib.sha256(raw).hexdigest()[:16], usable, excluded


def write_rating_sheet(run_dir: Path, outcomes: list[Outcome], items: dict[int, DatasetItem], rng: random.Random) -> None:
    """Blind sheet: explanations shuffled, condition hidden; the key file joins them back after rating."""
    rows = [(uuid.uuid4().hex[:8], o) for o in outcomes]
    rng.shuffle(rows)
    with (run_dir / "rating_sheet.csv").open("w", newline="") as f:
        w = csv.writer(f)
        # The book's explanation, when the dataset has one, is the reference to rate against.
        w.writerow(["rating_id", "question", "answer_shown", "explanation", "book_explanation", "rating (correct / partly / wrong)", "comment"])
        for rid, o in rows:
            item = items[o.entry_id]
            w.writerow([rid, item_text(item.question), o.answer, o.explanation, item.official_explanation, "", ""])
    with (run_dir / "rating_key.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rating_id", "entry_id", "condition", "answer_correct"])
        for rid, o in rows:
            w.writerow([rid, o.entry_id, o.condition, o.correct])


class Remembering:
    """A model whose system prompts carry the lessons learned for this item's sub-type (the memory)."""

    def __init__(self, llm: StructuredLLM, lessons: list[str]):
        self.llm, self.model = llm, llm.model
        self.note = "\n\nLESSONS FROM EARLIER QUESTIONS OF THIS TYPE (apply them when they fit):\n" + "\n".join(f"- {r}" for r in lessons)

    async def complete(self, system, user, schema, **kw):
        return await self.llm.complete(system + self.note, user, schema, **kw)


async def run(
    items: list[DatasetItem],
    conditions: list[str],
    primary: StructuredLLM,
    solver: StructuredLLM,
    judge: ArgumentJudge | None,
    seed: int = 7,
    concurrency: int = 4,
    memory: dict[str, list[str]] | None = None,
) -> list[Outcome]:
    rng = random.Random(seed)
    gate = asyncio.Semaphore(concurrency)
    same_model = getattr(primary, "model", "a") == getattr(solver, "model", "b")
    b2_label = "B2'" if same_model else "B2"

    async def one(item: DatasetItem, cond: str) -> Outcome | None:
        p, s = primary, solver
        lessons = (memory or {}).get(item.subtype) or (memory or {}).get("*")
        if memory is not None and lessons:
            p, s = Remembering(primary, lessons), Remembering(solver, lessons)
        suffix = "+M" if memory is not None else ""
        async with gate:
            try:
                out = None
                if cond == "B0":
                    out = await run_b0(p, item)
                elif cond == "B1":
                    out = await run_b1(p, s, judge, item, random.Random(rng.random()))
                elif cond == "B2":
                    out = await run_b2(p, s, item, b2_label)
                if out is not None:
                    out.condition += suffix
                return out
            except Exception as e:  # noqa: BLE001 — recorded, not fatal: one bad call should not lose the run
                print(f"[E1] item {item.entry_id} {cond}: {e}", file=sys.stderr)
            return None

    results = await asyncio.gather(*(one(i, c) for i in items for c in conditions))
    return [r for r in results if r is not None]


def main(argv: list[str] | None = None) -> None:
    from .app import build_judge
    from .config import load_settings
    from .llm import make_llm

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dataset", type=Path)
    ap.add_argument("--conditions", default="B0,B1,B2")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", type=Path, default=Path.home() / "questionize-research" / "runs")
    ap.add_argument("--ledger", type=Path, default=ROOT.parent.parent / "research" / "ledger.jsonl")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--split", choices=["all", "train", "test"], default="all", help="items of one split only (set by eval_e4)")
    ap.add_argument("--memory", type=Path, help="lessons learned on the train split (questionize.memory); conditions become B0+M, …")
    ap.add_argument("--baseline", type=Path, help="run directory of the same conditions without memory, to pair against")
    args = ap.parse_args(argv)

    settings = load_settings()
    primary = make_llm(settings.primary, timeout=settings.timeout_seconds)
    solver = make_llm(settings.solver, timeout=settings.timeout_seconds) if settings.solver != settings.primary else primary
    judge = build_judge(settings, primary, solver)
    dataset_id, dataset_hash, items, excluded = load_dataset(args.dataset)
    if args.split != "all":
        items = [i for i in items if i.split == args.split]
    if args.limit:
        items = items[: args.limit]
    memory = json.loads(args.memory.read_text())["lessons"] if args.memory else None
    baseline = load_baseline(args.baseline) if args.baseline else None
    conditions = [c.strip() for c in args.conditions.split(",") if c.strip()]

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]
    started = datetime.now(timezone.utc).isoformat()
    outcomes = asyncio.run(run(items, conditions, primary, solver, judge, seed=args.seed, memory=memory))
    summary = summarize(outcomes, seed=args.seed, baseline=baseline)

    run_dir = args.out / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "run_id": run_id, "protocol": PROTOCOL, "protocol_version": PROTOCOL_VERSION, "capabilities": CAPABILITIES, "started_at": started,
        "git_sha": git_sha(), "prompts_hash": prompts_hash(),
        "models": {"primary": settings.primary.model, "solver": settings.solver.model},
        "providers": {"primary": settings.primary.name, "solver": settings.solver.name},
        "judge": {"version": judge.version if judge else None, "samples_per_judge": settings.judge_samples, "override_rate": JUDGE_OVERRIDE_RATE},
        "seed": args.seed, "conditions": conditions,
        "dataset_id": dataset_id, "dataset_hash": dataset_hash, "n_items": len(items), "excluded": excluded,
        "split": args.split,
        "memory": {"hash": hashlib.sha256(args.memory.read_bytes()).hexdigest()[:16], "lessons": sum(len(v) for v in memory.values())} if memory else None,
        "baseline_run": args.baseline.name if args.baseline else None,
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=1))
    with (run_dir / "results.jsonl").open("w") as f:
        for o in outcomes:
            f.write(json.dumps(o.__dict__ | {"correct": o.correct}) + "\n")
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=1))
    write_rating_sheet(run_dir, outcomes, {i.entry_id: i for i in items}, random.Random(args.seed))

    # The ledger holds identifiers and aggregate numbers only: no item text, no local paths.
    line = {k: manifest[k] for k in ("run_id", "protocol", "protocol_version", "capabilities", "started_at", "git_sha", "prompts_hash", "models", "judge", "dataset_id", "dataset_hash", "n_items", "excluded", "split", "memory", "baseline_run")}
    line["summary"] = summary
    args.ledger.parent.mkdir(parents=True, exist_ok=True)
    with args.ledger.open("a") as f:
        f.write(json.dumps(line) + "\n")

    print(json.dumps(summary, indent=1))
    print(f"\nRun {run_id}: {run_dir}\nRate explanations blind in {run_dir / 'rating_sheet.csv'}; the ledger line was appended to {args.ledger}.")


if __name__ == "__main__":
    main()
