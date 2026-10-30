"""Private local E11 worker. Uploads only rules, hashes and correctness flags.

python -m questionize.local_research_worker --config PRIVATE_CONFIG [--once]
Configuration holds server URL, scoped token, local dataset and private artifact directory.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import time
import subprocess
from pathlib import Path

import httpx

from .config import load_settings
from .eval_e1 import load_dataset
from .evolution import content_hash
from .llm import OpenAICompatLLM
from .memory_research import propose
from .schemas import LearningMemory, SourceQuestion
from .upload_learning import fingerprint, solve

SOURCE_FILES = ("local_research_worker.py", "memory_research.py", "upload_learning.py", "schemas.py", "llm.py", "prompts.py", "pipeline.py", "integrity.py")


def source_hash():
    import hashlib
    return hashlib.sha256(b"".join(Path(__file__).with_name(name).read_bytes() for name in SOURCE_FILES)).hexdigest()


LOADED_SOURCE_HASH = source_hash()


def private_write(path, data):
    temporary = path.with_suffix(path.suffix + ".tmp")
    with os.fdopen(os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as handle:
        handle.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def prepare_data(config, lease):
    paths = [Path(p).expanduser().resolve() for p in config.get("datasets", [config.get("dataset", "")])]
    items, hashes = [], []
    for path in paths:
        if path.is_relative_to(Path(__file__).resolve().parents[2]):
            raise ValueError("Research originals must be outside the repository")
        dataset_id, digest, loaded, excluded = load_dataset(path)
        items.extend(loaded)
        hashes.append(digest)
    digest = hashes[0] if len(hashes) == 1 else content_hash(sorted(hashes))
    triggered = {o["question_fingerprint"] for o in lease["observations"]}
    def fp(i):
        return fingerprint(SourceQuestion(**i.question.model_dump()))
    for item in items:
        if item.split == "completion_validation":
            item.split = "test"
            continue
        if item.split not in ("train", "test"):
            item.split = "test" if int(fp(item)[:8], 16) % 5 == 0 else "train"
    heldout_groups = {fp(i) for i in items if i.split == "test"}
    # An alias in a second edition cannot move a validation group into training.
    train = [i for i in items if i.split == "train" and i.key_verdict == "book" and fp(i) not in heldout_groups]
    validation = list({fp(i): i for i in items if i.split == "test" and i.key_verdict == "book"}.values())
    train_hashes = {fp(i) for i in train}
    validation = [i for i in validation if fp(i) not in triggered | train_hashes]
    # Membership is frozen before any proposal. Cover subtypes, then fill deterministically.
    rng = random.Random(11)
    rng.shuffle(validation)
    # Completion was previously wholly absent. Keep a reserved format stratum,
    # as well as subtype coverage, rather than letting a random sample omit it.
    from .integrity import is_completion
    selected = [i for i in validation if is_completion(i.question.stem)][:4]
    covered = {i.subtype for i in selected}
    for i in validation:
        if i.subtype not in covered:
            selected.append(i)
            covered.add(i.subtype)
    selected += [i for i in validation if i not in selected]
    selected = selected[:int(config.get("validation_items", 16))]
    if len(selected) < 12 or len({fp(i) for i in selected}) != len(selected):
        raise ValueError("Insufficient independent source-keyed validation")
    validation_hashes = sorted(fp(i) for i in selected)
    registration = {"dataset_hash": digest, "validation_hash": content_hash(validation_hashes), "training_hash": content_hash(sorted(train_hashes)),
        "n_items": len(selected), "repeats": 2, "validation_label_source": "source_reference",
        "validation_fingerprints": validation_hashes, "training_fingerprints": sorted(train_hashes)}
    # Separate private teacher context from usage-derived hypotheses; never retrieve test items.
    types = {o["subtype"] for o in lease["observations"]}
    examples = [{"subtype": i.subtype, "question": i.question.model_dump(), "reference_key": i.answer_key,
                 "expert_explanation": i.official_explanation} for i in train if i.subtype in types][:3]
    reference_file = config.get("method_references")
    if reference_file:
        import hashlib
        path = Path(reference_file).expanduser().resolve()
        if path.is_relative_to(Path(__file__).resolve().parents[2]):
            raise ValueError("Reference archives must remain private")
        reference = json.loads(path.read_text())
        if reference.get("namespace") != "ai_derived_from_open_reference":
            raise ValueError("Reference origin must be explicit")
        for unit in reference.get("units", []):
            if unit.get("license") != "CC-BY-4.0" or not unit.get("source_sha256"):
                raise ValueError("Missing method reference rights or provenance")
            if types.intersection(unit["subtypes"]):
                examples.append({"kind": "attributed_method_reference", "subtype": unit["subtypes"],
                    "reference_method": unit["lesson"], "source": unit["source_id"], "source_sha256": unit["source_sha256"]})
        # Bind the candidate's input registration to references as well as item data.
        registration["dataset_hash"] = content_hash({"item_dataset_hash": digest,
            "method_reference_hash": hashlib.sha256(path.read_bytes()).hexdigest()})
    return selected, registration, examples


async def execute(config, lease, post):
    root = Path(config["artifacts"]).expanduser().resolve()
    root.mkdir(parents=True, mode=0o700, exist_ok=True)
    if root.is_relative_to(Path(__file__).resolve().parents[2]):
        raise ValueError("Private artifacts cannot be written into the repository")
    run = root / lease["id"]
    run.mkdir(mode=0o700, exist_ok=True)
    selected, registration, examples = prepare_data(config, lease)
    sources = Path(__file__).parent
    if source_hash() != LOADED_SOURCE_HASH:
        raise RuntimeError("Restart local worker after source changes")
    registration.update(worker_source_hash=LOADED_SOURCE_HASH, model=load_settings().primary.model,
        source_revision=subprocess.run(["git", "rev-parse", "HEAD"], cwd=sources, capture_output=True, text=True).stdout.strip())
    snapshot = run / "source"
    snapshot.mkdir(exist_ok=True)
    for path in sources.glob("*.py"):
        (snapshot / path.name).write_bytes(path.read_bytes())
    private_write(run / "registration.json", registration)
    private_write(run / "private-teacher-context.json", examples)
    private_write(run / "lease.json", {k: v for k, v in lease.items() if k != "lease"})
    settings = load_settings()
    if settings.primary.name != "meta":
        raise ValueError("E11 uses Meta")
    model = OpenAICompatLLM(settings.primary, timeout=75, max_retries=0)
    model._client = model._client.with_options(max_retries=0)
    async def heartbeat():
        while True:
            if source_hash() != LOADED_SOURCE_HASH:
                print(json.dumps({"status": "source_changed_restart_required"}), flush=True)
                return
            await asyncio.sleep(30)
            try:
                await asyncio.to_thread(post, "/heartbeat", {})
            except httpx.HTTPError:
                pass
    pulse = asyncio.create_task(heartbeat())
    try:
        try:
            payload, hypothesis = await propose(model, lease["baseline"]["payload"], lease["observations"], examples,
                audit=lambda p, h: private_write(run / "candidate.json", {"payload": p, "hypothesis": h}))
        except ValueError:
            result = post(f"/{lease['id']}/failure", {"lease": lease["lease"], "reason": "no_usable_candidate"})
            private_write(run / "server-result.json", result)
            print(json.dumps({"cycle": lease["id"], "status": "held", "reason": "candidate_rejected_before_validation"}), flush=True)
            return
        if payload == lease["baseline"]["payload"]:
            result = post(f"/{lease['id']}/failure", {"lease": lease["lease"], "reason": "no_usable_candidate"})
            private_write(run / "server-result.json", result)
            print(json.dumps({"cycle": lease["id"], "status": "held", "reason": "unchanged_candidate"}), flush=True)
            return
        registered = post(f"/{lease['id']}/candidate", {"lease": lease["lease"], "payload": payload, "registration": registration})
        candidate_meta = registered["candidate"]
        baseline = LearningMemory.model_validate(lease["baseline"])
        candidate = LearningMemory.model_validate({"id": candidate_meta["id"], "version": candidate_meta["version"], "hash": candidate_meta["content_hash"], "payload": payload})
        proofs, private_rows = [], []
        gate = asyncio.Semaphore(2)
        async def one(item, repeat):
            question = SourceQuestion(**item.question.model_dump())
            async with gate:
                # Randomize call order deterministically; each model call has isolated messages.
                policies = [baseline, candidate] if (item.entry_id + repeat) % 2 else [candidate, baseline]
                outcomes = {}
                for policy in policies:
                    outcomes[policy.id] = await solve(model, question, policy)
                b, c = outcomes[baseline.id], outcomes[candidate.id]
                row = {"case_hash": fingerprint(question), "round": repeat, "baseline_correct": b["answer_label"] == item.answer_key,
                       "candidate_correct": c["answer_label"] == item.answer_key}
                proofs.append(row)
                private_rows.append({**row, "source_key": item.answer_key, "question": question.model_dump(), "baseline": b, "candidate": c})
                private_write(run / "private-results.json", private_rows)
        await asyncio.gather(*(one(item, repeat) for repeat in (1, 2) for item in selected))
        result = post(f"/{lease['id']}/report", {"lease": lease["lease"], "baseline_hash": baseline.hash, "candidate_hash": candidate.hash, "proofs": proofs})
        private_write(run / "server-result.json", result)
        print(json.dumps({"cycle": lease["id"], "status": result["status"], "validation_items": len(selected), "model_calls": 1 + 4 * len(selected)}), flush=True)
    finally:
        pulse.cancel()
        await model._client.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    base = config["server"].rstrip("/") + "/api/v1/research/worker"
    token = Path(config["token_file"]).expanduser().read_text().strip()
    with httpx.Client(headers={"Authorization": "Bearer " + token}, timeout=30) as client:
        def post(path, payload):
            response = client.post(base + path, json=payload)
            response.raise_for_status()
            return None if response.status_code == 204 else response.json()
        while True:
            if source_hash() != LOADED_SOURCE_HASH:
                print(json.dumps({"status": "source_changed_restart_required"}), flush=True)
                return
            lease = None
            try:
                lease = post("/lease", {})
                if lease:
                    asyncio.run(execute(config, lease, post))
            except Exception as error:
                print(json.dumps({"status": "worker_error", "type": type(error).__name__}), flush=True)
                if lease:
                    try:
                        post(f"/{lease['id']}/failure", {"lease": lease["lease"], "reason": "provider_failure" if isinstance(error, (httpx.HTTPError, RuntimeError)) else "local_dataset_unavailable"})
                    except Exception:
                        pass
            if args.once:
                break
            time.sleep(10)


if __name__ == "__main__":
    main()
