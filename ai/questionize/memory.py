"""Learn a memory of solving lessons from keyed items (the train split), without retraining the model.

    python -m questionize.memory ~/private/official-cr-v1.json --out ~/questionize-research/memory/cr-v1.json

For every train item the model first solves it blind. It then sees the book's key and explanation and
writes, in its own words, the general lesson a test-taker should carry to other questions of the same
sub-type (what it missed, or what it got right for the right reason). Lessons are consolidated per sub-type
into a short list of rules. That list is the memory E1 tests on the held-out test split (ExpeL, Zhao et al.
2024; Dynamic Cheatsheet, Suzgun et al. 2025): improvement from accumulated, key-checked experience.

The lessons hold no item text: each is checked against the item's passage, options and explanation and
dropped if it shares a run of 8 or more words with them.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from .eval_e1 import DatasetItem, item_text, load_dataset
from .llm import StructuredLLM
from .pipeline import longest_copied_run
from .schemas import SolverResult

MAX_COPIED_WORDS = 7
RULES_PER_SUBTYPE = 8

SOLVE_SYSTEM = "You are an expert GMAT/LSAT test-taker. Solve the question; report your honest confidence."

REFLECT_SYSTEM = """You coach GMAT/LSAT reasoning. You just answered a question; below are your answer and \
reasoning, and the book's key and explanation. Write the one general lesson a test-taker should carry to \
OTHER questions of the same type: a rule about how to read the stem, find the conclusion or gap, or reject a \
kind of tempting option. If you were wrong, the lesson is what would have prevented the mistake; if you were \
right, it is the move that made you right. Use your own words. Never mention this question's topic, names, \
numbers or wording, and never quote the explanation."""

CONSOLIDATE_SYSTEM = f"""You keep a short playbook for one GMAT/LSAT question type. Merge the lessons below \
into at most {RULES_PER_SUBTYPE} rules: combine duplicates, keep the ones learned from mistakes, drop vague or \
topic-specific ones, and order them by how often they would change an answer. Each rule is one sentence, \
general, in your own words."""


class Lesson(BaseModel):
    lesson: str = Field(..., max_length=300)
    from_mistake: bool


class Playbook(BaseModel):
    rules: list[str] = Field(..., max_length=RULES_PER_SUBTYPE)


def leaks(text: str, item: DatasetItem) -> bool:
    q = item.question
    source = "\n".join([q.passage, q.stem, *(c["text"] for c in q.choices), item.official_explanation])
    return longest_copied_run(text, source)[0] > MAX_COPIED_WORDS


async def reflect(model: StructuredLLM, item: DatasetItem) -> tuple[Lesson | None, bool]:
    solved = await model.complete(SOLVE_SYSTEM, item_text(item.question), SolverResult, temperature=0.0)
    correct = solved.answer_label == item.answer_key
    context = (
        f"{item_text(item.question)}\n\nYOUR ANSWER: {solved.answer_label} (confidence {solved.confidence:.2f})\n"
        f"YOUR REASONING: {solved.reasoning}\n\nBOOK'S KEY: {item.answer_key}\nBOOK'S EXPLANATION: {item.official_explanation or '(none)'}"
    )
    lesson = await model.complete(REFLECT_SYSTEM, context, Lesson, temperature=0.0)
    return (None if leaks(lesson.lesson, item) else lesson), correct


async def learn(model: StructuredLLM, items: list[DatasetItem], concurrency: int = 4) -> tuple[dict[str, list[str]], dict]:
    gate = asyncio.Semaphore(concurrency)

    async def one(item: DatasetItem):
        async with gate:
            try:
                return item, *(await reflect(model, item))
            except Exception as e:  # noqa: BLE001 — one failed item should not lose the run
                print(f"[memory] item {item.entry_id}: {e}", file=sys.stderr)
                return item, None, None

    by_type: dict[str, list[Lesson]] = defaultdict(list)
    stats = {"items": len(items), "solved_correctly": 0, "lessons": 0, "dropped_for_copying": 0}
    for item, lesson, correct in await asyncio.gather(*(one(i) for i in items)):
        stats["solved_correctly"] += bool(correct)
        if lesson is None:
            stats["dropped_for_copying"] += correct is not None
            continue
        stats["lessons"] += 1
        by_type[item.subtype or "*"].append(lesson)

    memory: dict[str, list[str]] = {}
    for subtype, lessons in sorted(by_type.items()):
        ordered = sorted(lessons, key=lambda lesson: not lesson.from_mistake)
        listing = "\n".join(f"- {'[mistake] ' if x.from_mistake else ''}{x.lesson}" for x in ordered)
        book = await model.complete(CONSOLIDATE_SYSTEM, f"QUESTION TYPE: {subtype}\n\nLESSONS:\n{listing}", Playbook, temperature=0.0)
        memory[subtype] = [r for r in book.rules if r.strip()]
    return memory, stats


def main(argv: list[str] | None = None) -> None:
    from .config import load_settings
    from .llm import make_llm

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dataset", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--split", default="train")
    ap.add_argument("--limit", type=int, default=0, help="learn from the first N items only (a trial run)")
    args = ap.parse_args(argv)

    settings = load_settings()
    model = make_llm(settings.primary, timeout=settings.timeout_seconds)
    dataset_id, dataset_hash, items, _ = load_dataset(args.dataset)
    items = [i for i in items if i.split == args.split] if args.split != "all" else items
    if args.limit:
        items = items[: args.limit]
    if not items:
        sys.exit(f"No usable items in split {args.split!r}; run questionize.eval_e4 first to assign splits.")
    memory, stats = asyncio.run(learn(model, items))
    out = {
        "dataset_id": dataset_id, "dataset_hash": dataset_hash, "split": args.split, "model": settings.primary.model,
        "created_at": datetime.now(timezone.utc).isoformat(), "stats": stats, "lessons": memory,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1))
    digest = hashlib.sha256(args.out.read_bytes()).hexdigest()[:16]
    print(json.dumps(stats))
    for subtype, rules in memory.items():
        print(f"\n[{subtype}]")
        for rule in rules:
            print(f"  - {rule}")
    print(f"{sum(len(v) for v in memory.values())} rules for {len(memory)} sub-types → {args.out} (hash {digest})")


if __name__ == "__main__":
    main()
