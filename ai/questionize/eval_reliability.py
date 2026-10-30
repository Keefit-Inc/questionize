"""E9/E10 live evaluation with private per-case outputs and aggregate-only ledger entries."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import random
import re
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import prompts
from .eval_e1 import explain, git_sha, item_text, load_dataset, wilson
from .integrity import integrity_issues
from .judge import ArgumentJudge, SUBTYPE_MEASURES, rank
from .operator_policy import task_operator
from .pipeline import QuestionPipeline
from .schemas import Question, SolverResult


class Counted:
    def __init__(self, llm):
        self.llm, self.model, self.calls = llm, llm.model, 0

    async def complete(self, *args, **kwargs):
        self.calls += 1
        return await self.llm.complete(*args, **kwargs)


def rate(k, n):
    return {"correct": k, "n": n, "accuracy": round(k / n, 4) if n else None, "ci95": wilson(k, n) if n else None}


def defect_cases(items, version=1):
    parents = []
    for subtype in ("strengthen", "weaken", "assumption"):
        parents += [i for i in items if i.subtype == subtype][:2]
    parents += [i for i in items if "bold" in i.question.stem.lower()][:2]
    cases = []
    for item in parents:
        other = next(c["label"] for c in item.question.choices if c["label"] != item.answer_key)
        rationales = {r["label"]: r["text"] for r in item.option_explanations} if version >= 2 else {}
        traps = {r["label"]: r["trap"] for r in item.option_traps} if version >= 2 else {}
        q = Question(type="CR", subtype=item.subtype, **item.question.model_dump(), correct_label=item.answer_key,
            explanation=item.official_explanation, skill=item.subtype,
            choice_rationales=[{"label": c["label"], "rationale": rationales.get(c["label"], "See the explanation."),
                "trap": "correct" if c["label"] == item.answer_key else traps.get(c["label"], "unsupported")} for c in item.question.choices])
        cases.append((item.entry_id, "valid_control", q))
        wrong = q.model_copy(deep=True)
        wrong.correct_label = other
        for r in wrong.choice_rationales:
            r.trap = "correct" if r.label == other else "unsupported"
        cases.append((item.entry_id, "wrong_key", wrong))
        duplicate = q.model_copy(deep=True)
        key_text = next(c.text for c in q.choices if c.label == q.correct_label)
        next(c for c in duplicate.choices if c.label == other).text = key_text
        cases.append((item.entry_id, "duplicate_correct_option", duplicate))
        contradiction = q.model_copy(deep=True)
        contradiction.explanation = f"Option {q.correct_label} is incorrect. The only correct answer is option {other}."
        cases.append((item.entry_id, "contradictory_explanation", contradiction))
        if "bold" in q.stem.lower():
            missing = q.model_copy(deep=True)
            missing.passage = re.sub(r"\[/?BOLD_\d+\]", "", missing.passage)
            cases.append((item.entry_id, "missing_emphasis", missing))
    return cases


async def e9_one(llm, item, version=1):
    counted = Counted(llm)
    solved = await counted.complete(prompts.SOLVER_SYSTEM, item_text(item.question), SolverResult, temperature=0)
    result = {"entry_id": item.entry_id, "key": item.answer_key, "solver_answer": solved.answer_label,
              "solver_correct": solved.answer_label == item.answer_key, "subtype": item.subtype,
              "operator": task_operator(item.question.stem), "solver_confidence": solved.confidence}
    legacy = guarded = solved.answer_label
    if item.subtype in SUBTYPE_MEASURES:
        judge = ArgumentJudge([counted], seed=item.entry_id)
        samples = await judge.sample(item.question.passage, item.question.stem, [(c["label"], c["text"]) for c in item.question.choices])
        measure, direction = SUBTYPE_MEASURES[item.subtype]
        top, stability, margin, _ = rank(samples, measure, direction, random.Random(item.entry_id))
        result.update(judge_answer=top, judge_correct=top == item.answer_key, stability=stability, margin=margin)
        if stability >= 0.8:
            legacy = top
            if result["operator"] != "except":
                guarded = top
    result.update(legacy_answer=legacy, guarded_answer=guarded,
                  legacy_correct=legacy == item.answer_key, guarded_correct=guarded == item.answer_key)
    if version == 1:
        try:
            explanation, objects = await explain(counted, item, guarded)
            result.update(explanation=explanation, explainer_objects=objects)
        except Exception as e:
            result["explanation_error"] = type(e).__name__
    result["calls"] = counted.calls
    return result


async def e10_one(llm, case):
    parent, kind, question = case
    counted = Counted(llm)
    # Published reference inputs are not article-copy candidates. Isolate semantic verification.
    pipeline = QuestionPipeline(counted, counted, max_revisions=0, max_copied_words=100_000, judge=None, integrity_checks=False)
    async def emit(_):
        pass
    outcome = await pipeline.verify(0, "Research candidate", question.passage, question, "CR", emit)
    defects = integrity_issues(question)
    legacy = outcome.verification.verified
    return {"entry_id": parent, "kind": kind, "expected_valid": kind == "valid_control", "legacy_accepted": legacy,
            "guarded_accepted": legacy and not defects, "integrity_issues": defects, "calls": counted.calls,
            "verification": outcome.verification.model_dump(), "candidate": question.model_dump()}


def aggregate(protocol, results, expected):
    good = [r for r in results if "error" not in r]
    summary = {"expected": expected, "completed": len(good), "errors": len(results) - len(good),
               "calls": sum(r.get("calls", 0) for r in results)}
    if protocol == "E9":
        for field in ("solver", "legacy", "guarded"):
            summary[field] = rate(sum(r[f"{field}_correct"] for r in good), len(good))
        judged = [r for r in good if "judge_correct" in r]
        summary["judge"] = rate(sum(r["judge_correct"] for r in judged), len(judged))
        summary["judge"]["coverage"] = round(len(judged) / expected, 4) if expected else 0
        for policy in ("legacy", "guarded"):
            summary[policy].update(corrected=sum(not r["solver_correct"] and r[f"{policy}_correct"] for r in good),
                                   corrupted=sum(r["solver_correct"] and not r[f"{policy}_correct"] for r in good))
        summary["unrated_explanations"] = sum("explanation" in r for r in good)
        summary["explanation_errors"] = sum("explanation_error" in r for r in good)
    else:
        summary["parents"] = len({r["entry_id"] for r in good})
        summary["by_type"] = {}
        for kind in sorted({r["kind"] for r in good}):
            rows = [r for r in good if r["kind"] == kind]
            summary["by_type"][kind] = {"n": len(rows), "legacy_accepted": sum(r["legacy_accepted"] for r in rows),
                "guarded_accepted": sum(r["guarded_accepted"] for r in rows), "deterministically_blocked": sum(bool(r["integrity_issues"]) for r in rows)}
        defects = [r for r in good if not r["expected_valid"]]
        for policy in ("legacy", "guarded"):
            summary[policy] = {"n": len(defects), "rejected": sum(not r[f"{policy}_accepted"] for r in defects),
                "false_accepts": sum(r[f"{policy}_accepted"] for r in defects)}
    return summary


async def evaluate(args, items, llm, run_dir):
    cases = items if args.protocol == "E9" else defect_cases(items, args.version)
    if args.smoke:
        if args.protocol == "E9":
            # Exercise repaired boldface, EXCEPT and an ordinary judged item.
            cases = list(dict.fromkeys(i.entry_id for i in items if "bold" in i.question.stem.lower()))[:1]
            cases = [next(i for i in items if i.entry_id == e) for e in cases]
            for pred in (lambda i: task_operator(i.question.stem) == "except", lambda i: i.subtype == "assumption"):
                candidate = next((i for i in items if pred(i) and i not in cases), None)
                if candidate:
                    cases.append(candidate)
        else:
            cases = cases[:4] + [next(c for c in cases if c[1] == "missing_emphasis")]
    gate = asyncio.Semaphore(3)
    results = []
    async def one(case):
        async with gate:
            started = time.monotonic()
            try:
                r = await asyncio.wait_for(e9_one(llm, case, args.version) if args.protocol == "E9" else e10_one(llm, case), timeout=480)
            except Exception as e:
                r = {"entry_id": case.entry_id if args.protocol == "E9" else case[0], "error": type(e).__name__}
            r["elapsed_seconds"] = round(time.monotonic() - started, 2)
            results.append(r)
            with (run_dir / "results.jsonl").open("a") as f:
                f.write(json.dumps(r) + "\n")
            print(f"{args.protocol}: {len(results)}/{len(cases)} complete; errors={sum('error' in x for x in results)}", flush=True)
    await asyncio.gather(*(one(c) for c in cases))
    return aggregate(args.protocol, results, len(cases)), results


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("dataset", type=Path)
    p.add_argument("--protocol", choices=["E9", "E10"], required=True)
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--version", type=int, choices=[1, 2], default=1)
    args = p.parse_args()
    from .config import load_settings
    from .llm import OpenAICompatLLM
    settings = load_settings()
    if settings.primary.name != "meta":
        raise SystemExit("This registered evaluation uses Meta")
    model = OpenAICompatLLM(settings.primary, timeout=150, max_retries=0)
    model._client = model._client.with_options(max_retries=0)
    dataset, hash_, items, excluded = load_dataset(args.dataset)
    items = [i for i in items if i.split == "test"]
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + args.protocol.lower() + "-" + uuid.uuid4().hex[:6]
    run_dir = Path.home() / "questionize-research" / "runs" / run_id
    run_dir.mkdir(mode=0o700)
    manifest = {"run_id": run_id, "protocol": args.protocol, "protocol_version": args.version, "request_timeout_seconds": 150,
        "started_at": datetime.now(timezone.utc).isoformat(), "git_sha": git_sha(), "dataset_id": dataset,
        "dataset_hash": hash_, "split": "development_test", "evaluation_scope": "trial" if args.smoke else "full",
        "models": {"primary": model.model}, "source_namespace": "expert_reference", "reference_explanations_private": True,
        "excluded": excluded, "max_retries": 0, "concurrency": 3,
        "working_tree_dirty": bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=Path(__file__).parent).stdout.strip()),
        "prompts_hash": hashlib.sha256(b"".join(Path(__file__).with_name(f).read_bytes() for f in
            ("eval_reliability.py", "integrity.py", "pipeline.py", "judge.py", "prompts.py", "operator_policy.py"))).hexdigest()}
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    snapshot = run_dir / "source"
    snapshot.mkdir()
    for source in Path(__file__).parent.glob("*.py"):
        (snapshot / source.name).write_bytes(source.read_bytes())
    print("RUN", run_id, flush=True)
    summary, results = asyncio.run(evaluate(args, items, model, run_dir))
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    # Explicitly scoped metrics. E10's related mutations are not independent Bernoulli samples.
    entry = {**manifest, "subject": "CR", "capabilities": ["C3.1"] if args.protocol == "E9" else ["C3.4"],
        "n_items": summary["expected"], "summary": {}, "note": "Repaired-input development evaluation; no human explanation ratings or generalization claim." if args.protocol == "E9" else "Constructed, parent-clustered defect contracts; not a population reliability estimate."}
    if args.protocol == "E9":
        entry["summary"] = {k: summary[k] for k in ("solver", "legacy", "guarded")}
    else:
        entry["n_items"] = summary["guarded"]["n"]
        entry["summary"] = {k: {"capability_metrics": {"C3.4": {"value": summary[k]["rejected"] / summary[k]["n"] if summary[k]["n"] else 0,
            "n": summary[k]["n"]}}} for k in ("legacy", "guarded")}
    ledger = Path(__file__).resolve().parents[2] / "research" / "ledger.jsonl"
    with ledger.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    print(json.dumps(summary, indent=2), flush=True)
    print("PRIVATE OUTPUT", run_dir, flush=True)


if __name__ == "__main__":
    main()
