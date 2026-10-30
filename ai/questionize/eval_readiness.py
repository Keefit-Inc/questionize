"""Private E12 coverage and E2 v2 first-draft runs. Outputs contain source text: local only."""
from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import random
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import levels, prompts
from .cr_design import scaffold
from .eval_e1 import git_sha, wilson
from .integrity import integrity_issues
from .schemas import Question, SourceQuestion


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    path.chmod(0o600)


class Counted:
    def __init__(self, llm):
        self.llm, self.model, self.calls = llm, llm.model, 0

    async def complete(self, *args, **kwargs):
        self.calls += 1
        return await asyncio.wait_for(self.llm.complete(*args, **kwargs), timeout=90)


def rate(k, n):
    return {"n": n, "correct": k, "accuracy": k / n if n else None, "ci95": wilson(k, n) if n else None}


def tasks():
    objectives = {
        "strengthen": ("Assess whether evidence supports a proposed mechanism", "irrelevant"),
        "weaken": ("Distinguish a causal conclusion from a competing explanation", "reversal"),
        "assumption": ("Find a necessary bridge rather than a sufficient guarantee", "too_extreme"),
        "inference": ("Derive only what is entailed by the stated premises", "unsupported"),
        "explain": ("Reconcile two apparently conflicting observations", "half_right"),
    }
    topics = ["public bicycle repair stations", "seed storage in a community garden", "museum audio guides", "scheduling at a neighborhood clinic"]
    return [{"id": n * 4 + j, "subtype": sub, "objective": objective, "trap": trap, "topic": topic}
        for n, (sub, (objective, trap)) in enumerate(objectives.items()) for j, topic in enumerate(topics)]


async def completion(data, model, root):
    from .upload_learning import solve
    items = data["items"]
    fresh = [i for i in items if i.get("split") == "completion_validation"]
    old = [i for i in items if i.get("split") == "test"]
    if len(fresh) != 15 or len(old) != 39:
        raise ValueError("Registered cohort membership changed")
    controls = sum(not integrity_issues(SourceQuestion(**i["question"])) for i in items)
    blocked = 0
    for item in fresh:
        q = SourceQuestion(**item["question"])
        q.passage = q.passage.replace("____", "")
        blocked += "missing_completion_blank" in integrity_issues(q)
    write(root / "registered-membership.json", {"completion": [i["entry_id"] for i in fresh], "old_test": [i["entry_id"] for i in old]})
    results = []
    gate = asyncio.Semaphore(2)

    async def one(item, repeat):
        async with gate:
            counted = Counted(model)
            r = {"entry_id": item["entry_id"], "split": item["split"], "repeat": repeat}
            try:
                answer = await solve(counted, SourceQuestion(**item["question"]), None)
                r.update(answer=answer, correct=answer["answer_label"] == item["answer_key"])
            except Exception as e:
                r.update(correct=False, error=type(e).__name__)
            r["calls"] = counted.calls
            results.append(r)
            write(root / "private-results.json", results)
            print(f"E12 {len(results)}/69 completed; errors={sum('error' in x for x in results)}", flush=True)
    await asyncio.gather(*(one(i, 1) for i in fresh[:3]))
    if any("error" in r for r in results):
        raise RuntimeError("Smoke failed; private results retained")
    await asyncio.gather(*(one(i, repeat) for cohort, repeat in [(fresh[3:], 1), (fresh, 2), (old, 1)] for i in cohort))
    summary = {}
    for name, pred in [("completion_first", lambda r:r["split"] == "completion_validation" and r["repeat"] == 1),
                       ("completion_repeat", lambda r:r["split"] == "completion_validation" and r["repeat"] == 2),
                       ("previous_test", lambda r:r["split"] == "test")]:
        rows = [r for r in results if pred(r)]
        summary[name] = rate(sum(r["correct"] for r in rows), len(rows))
    repeats = {r["entry_id"]: r for r in results if r["repeat"] == 2}
    summary["format_contract"] = {"normal_accepted": controls, "normal_n": len(items), "missing_blank_blocked": blocked, "defect_n": len(fresh)}
    summary["repeat_disagreements"] = sum(r.get("answer", {}).get("answer_label") != repeats[r["entry_id"]].get("answer", {}).get("answer_label") for r in results if r["split"] == "completion_validation" and r["repeat"] == 1)
    summary.update(expected=69, completed=len(results), errors=sum("error" in r for r in results), calls=sum(r["calls"] for r in results))
    return summary


async def generation(model, root):
    from .judge import ArgumentJudge
    from .pipeline import QuestionPipeline, normalize_question
    registered = tasks()
    write(root / "registered-tasks.json", registered)
    results = []

    async def one(task, condition):
        counted = Counted(model)
        r = {"pair": task["id"], "condition": condition}
        try:
            pattern = {"family":"CR", "subtype":task["subtype"], "competency":task["objective"], "key_rule":task["objective"], "distractor_traps":[task["trap"]]}
            system = prompts.PATTERN_WRITER_SYSTEM + ("\n" + scaffold(task["subtype"]) if condition == "candidate" else "")
            draft = normalize_question(await counted.complete(system, prompts.pattern_writer_user(json.dumps(pattern), task["trap"], "medium", task["topic"], levels.brief("gmat")), Question, temperature=0.8), "CR")
            write(root / f"draft-{task['id']}-{condition}.json", draft.model_dump())
            pipeline = QuestionPipeline(counted, counted, max_revisions=0,
                judge=ArgumentJudge([counted], samples_per_judge=3, seed=task["id"]))
            async def emit(_):
                pass
            verified = await pipeline.verify(task["id"], "", "", draft, "CR", emit)
            r.update(passed=verified.verification.verified, result=verified.model_dump())
        except Exception as e:
            r.update(passed=False, error=type(e).__name__)
        r["calls"] = counted.calls
        results.append(r)
        write(root / "private-results.json", results)
        print(f"E2 {len(results)}/40 completed; errors={sum('error' in x for x in results)}", flush=True)

    async def pair(task):
        for cond in (["baseline", "candidate"] if task["id"] % 2 == 0 else ["candidate", "baseline"]):
            await one(task, cond)
    await asyncio.gather(*(pair(task) for task in registered[:2]))
    if any("error" in r for r in results):
        raise RuntimeError("Smoke failed; private results retained")
    gate = asyncio.Semaphore(2)
    async def limited(task):
        async with gate:
            await pair(task)
    await asyncio.gather(*(limited(task) for task in registered[2:]))
    summary = {}
    for cond in ["baseline", "candidate"]:
        rows = [r for r in results if r["condition"] == cond]
        n, k = len(rows), sum(r["passed"] for r in rows)
        summary[cond] = {"first_draft_pass_rate":k/n, "first_draft_pass_rate_n":n, "first_draft_pass_rate_ci95":wilson(k,n),
            "passed":k, "calls":sum(r["calls"] for r in rows), "errors":sum("error" in r for r in rows)}
    by = {(r["pair"],r["condition"]):r for r in results}
    gained = sum(not by[t["id"],"baseline"]["passed"] and by[t["id"],"candidate"]["passed"] for t in registered)
    lost = sum(by[t["id"],"baseline"]["passed"] and not by[t["id"],"candidate"]["passed"] for t in registered)
    summary.update(gained=gained, lost=lost, expected=40, completed=len(results), errors=sum("error" in r for r in results), calls=sum(r["calls"] for r in results))
    summary["adopt"] = gained > 0 and lost == 0 and summary["errors"] == 0 and len(results) == 40
    rng = random.Random(20261030)
    with (root / "private-blind-pairs.csv").open("w") as f:
        writer = csv.writer(f); writer.writerow(["pair", "left", "right", "preference", "wrong_key", "notes"])
        for task in registered:
            order = ["baseline", "candidate"]; rng.shuffle(order)
            writer.writerow([task["id"], json.dumps(by[task["id"],order[0]].get("result",{}).get("question",{})), json.dumps(by[task["id"],order[1]].get("result",{}).get("question",{})), "", "", ""])
    (root / "private-blind-pairs.csv").chmod(0o600)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("protocol", choices=["E12", "E2"])
    parser.add_argument("--dataset", type=Path)
    args = parser.parse_args()
    from .config import load_settings
    from .llm import OpenAICompatLLM
    settings = load_settings()
    if settings.primary.name != "meta":
        raise SystemExit("Registered runs use Meta")
    model = OpenAICompatLLM(settings.primary, timeout=90, max_retries=0)
    model._client = model._client.with_options(max_retries=0)
    root = Path.home() / "questionize-research" / "runs" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + args.protocol.lower() + "-" + uuid.uuid4().hex[:6])
    root.mkdir(mode=0o700)
    files = ["eval_readiness.py", "cr_design.py", "upload_learning.py", "integrity.py", "pipeline.py", "judge.py", "prompts.py"]
    snapshot = root / "source"; snapshot.mkdir(mode=0o700)
    for name in files:
        p = Path(__file__).with_name(name); (snapshot / name).write_bytes(p.read_bytes())
    manifest = {"run_id":root.name,"protocol":args.protocol,"protocol_version":1 if args.protocol == "E12" else 2,
        "started_at":datetime.now(timezone.utc).isoformat(),"git_sha":git_sha(),"subject":"CR","evaluation_scope":"development",
        "models":{"primary":model.model},"max_retries":0,"prompts_hash":hashlib.sha256(b"".join((snapshot/n).read_bytes() for n in files)).hexdigest()}
    data = None
    if args.protocol == "E12":
        if args.dataset is None: raise SystemExit("E12 requires a private dataset")
        data=json.loads(args.dataset.read_text()); manifest.update(dataset_id=data["dataset"],dataset_hash=hashlib.sha256(args.dataset.read_bytes()).hexdigest())
    else:
        manifest.update(dataset_id="original-cr-design-tasks-v1",dataset_hash=hashlib.sha256(json.dumps(tasks(),sort_keys=True).encode()).hexdigest())
    write(root/"manifest.json",manifest)
    print("PRIVATE RUN",root,flush=True)
    started=time.monotonic()
    summary=asyncio.run(completion(data,model,root) if data else generation(model,root))
    summary["wall_seconds"]=round(time.monotonic()-started,2)
    write(root/"summary.json",summary)
    conditions = {k:summary[k] for k in (["completion_first","completion_repeat","previous_test"] if data else ["baseline","candidate"])}
    entry={**manifest,"capabilities":["C3.1"] if data else ["C5"],"n_items":54 if data else 20,"summary":conditions,
        "note":"Development cohorts; repeated responses are not independent items. No human explanation/quality ratings or learner-benefit claim."}
    with (Path(__file__).resolve().parents[2]/"research/ledger.jsonl").open("a") as f:f.write(json.dumps(entry)+"\n")
    print(json.dumps(summary,indent=2),flush=True)


if __name__ == "__main__":
    main()
