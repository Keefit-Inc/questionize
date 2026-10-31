"""Original finite propositional exercises with exhaustive reference checks.

These are formal-logic microtasks, not GMAT questions or human-labelled learner
data. Named instances of one structure do not count as independent structures.
"""
from __future__ import annotations

import argparse
from collections import Counter
from itertools import product
import json
from pathlib import Path
import random

from .local_solver import digest, messages, private_json

STRUCTURES = {
    "train": ("chain2", "contraposition", "disjunction", "conjunctive_rule"),
    "development": ("chain3", "contra_chain2", "disjunctive_chain"),
    "confirmation": ("fork_join", "contra_chain3"),
}


def holds(formula, world):
    if isinstance(formula, int):
        return world[formula]
    op, *args = formula
    if op == "not":
        return not holds(args[0], world)
    if op == "and":
        return all(holds(a, world) for a in args)
    if op == "or":
        return any(holds(a, world) for a in args)
    if op == "implies":
        return not holds(args[0], world) or holds(args[1], world)
    raise ValueError("Unknown connective")


def valid_worlds(premises, atoms=4):
    return [w for w in product((False, True), repeat=atoms) if all(holds(p, w) for p in premises)]


def structure(name):
    structures = {
        "chain2": ([0, ("implies", 0, 1), ("implies", 1, 2)], 2),
        "contraposition": ([("implies", 0, 1), ("not", 1)], ("not", 0)),
        "disjunction": ([("or", 0, 1), ("not", 0)], 1),
        "conjunctive_rule": ([0, 1, ("implies", ("and", 0, 1), 2)], 2),
        "chain3": ([0, ("implies", 0, 1), ("implies", 1, 2), ("implies", 2, 3)], 3),
        "contra_chain2": ([("implies", 0, 1), ("implies", 1, 2), ("not", 2)], ("not", 0)),
        "disjunctive_chain": ([("or", 0, 1), ("not", 0), ("implies", 1, 2)], 2),
        "fork_join": ([0, ("implies", 0, 1), ("implies", 0, 2), ("implies", ("and", 1, 2), 3)], 3),
        "contra_chain3": ([("implies", 0, 1), ("implies", 1, 2), ("implies", 2, 3), ("not", 3)], ("not", 0)),
    }
    return structures[name]


def render(formula, atoms):
    if isinstance(formula, int):
        return atoms[formula]
    op, *args = formula
    if op == "not":
        return "it is not the case that " + render(args[0], atoms)
    if op in ("and", "or"):
        return "(" + (" and " if op == "and" else " or ").join(render(a, atoms) for a in args) + ")"
    if op == "implies":
        return "if " + render(args[0], atoms) + ", then " + render(args[1], atoms)
    raise ValueError("Unknown connective")


def derive(premises):
    """Independent forward closure for the supported Horn/disjunction structures."""
    facts = {p for p in premises if isinstance(p, int) or p[0] == "not"}
    steps = []
    changed = True
    def neg(p):
        return p[1] if isinstance(p, tuple) and p[0] == "not" else ("not", p)
    def known(p):
        return all(known(a) for a in p[1:]) if isinstance(p, tuple) and p[0] == "and" else p in facts
    while changed:
        changed = False
        for p in premises:
            if not isinstance(p, tuple):
                continue
            new = None
            if p[0] == "implies":
                a, b = p[1:]
                if known(a):
                    new = b
                elif neg(b) in facts and isinstance(a, int):
                    new = neg(a)
            elif p[0] == "or":
                a, b = p[1:]
                if neg(a) in facts:
                    new = b
                elif neg(b) in facts:
                    new = a
            if new is not None and new not in facts:
                facts.add(new)
                steps.append((p, new))
                changed = True
    return facts, steps


def exercise(name, seed, number):
    rng = random.Random(seed)
    verbs = ["registered", "tested", "approved", "eligible", "sealed", "inspected", "flagged", "calibrated"]
    rng.shuffle(verbs)
    noun = rng.choice(["device", "record", "package", "sample"])
    atoms = [f"the {noun} is {v}" for v in verbs[:4]]
    premises, key = structure(name)
    worlds = valid_worlds(premises)
    facts, steps = derive(premises)
    assert worlds and key in facts and all(holds(key, w) for w in worlds)
    candidates = list(range(4)) + [("not", i) for i in range(4)]
    wrong = [c for c in candidates if not all(holds(c, w) for w in worlds)]
    rng.shuffle(wrong)
    options = wrong[:4] + [key]
    rng.shuffle(options)
    ordered_premises = list(premises)
    rng.shuffle(ordered_premises)
    question = {"passage": "For this question, 'or' includes the case where both alternatives hold.\n" + "\n".join(
        render(p, atoms).capitalize() + "." for p in ordered_premises),
        "stem": "Which statement must be true, given only these conditions?",
        "choices": [{"label": chr(65+i), "text": render(p, atoms).capitalize() + "."} for i, p in enumerate(options)]}
    truth = [all(holds(c, w) for w in worlds) for c in options]
    assert sum(truth) == 1
    label = chr(65 + truth.index(True))
    explanation = " ".join(f"Using {render(rule, atoms)}, we can establish that {render(fact, atoms)}."
                           for rule, fact in steps)
    explanation += f" Therefore {render(key, atoms)} must hold.\nAnswer: {label}"
    return {"entry_id": number, "subtype": name, "structure_group": name,
            "question": question, "answer_key": label, "original_authored": True,
            "reference_origin": "exhaustive_boolean_enumeration_plus_independent_rule_derivation",
            "reference": {"premises": premises, "options": options, "satisfying_worlds": worlds},
            "explanation": explanation}


def prepare(out, instances=32, label_only=False):
    if out.exists():
        raise ValueError("Use a new curriculum directory; never overwrite a split")
    if instances < 2:
        raise ValueError("At least two instances per training structure")
    partitions = {}
    number = 960000
    for part, names in STRUCTURES.items():
        count = instances if part == "train" else 8
        partition = []
        for name in names:
            for n in range(count):
                number += 1
                seed = int(digest([part, name, n])[:16], 16)
                partition.append(exercise(name, seed, number))
        partitions[part] = partition
    out.mkdir(parents=True, mode=0o700)
    seen = set()
    for part, items in partitions.items():
        hashes = {digest(i["question"]) for i in items}
        assert len(hashes) == len(items) and not hashes & seen
        seen |= hashes
        private_json(out / (part + "-items.json"), {"items": items})
    # Validation loss is explicitly on development structures, never confirmation.
    for filename, part in (("train.jsonl", "train"), ("valid.jsonl", "development")):
        p = out / filename
        with p.open("w") as f:
            p.chmod(0o600)
            for item in partitions[part]:
                response = item["answer_key"] if label_only else item["explanation"]
                f.write(json.dumps({"messages": messages(item, "choice" if label_only else "base") + [
                    {"role": "assistant", "content": response}]}) + "\n")
    dev = partitions["development"]
    manifest = {"protocol": "E16-local-training-feasibility", "version": 1,
                "scope": "generated_formal_logic_development", "items": dev,
                "membership_hash": digest([i["question"] for i in dev]),
                "arms": {arm: digest(messages(dev[0], arm)[0]) for arm in ("base", "procedure", "choice")}}
    private_json(out / "development" / "manifest.json", manifest)
    summary = {"origin": "original_authored_programmatic", "scope": "finite_propositional_logic_only",
               "instances": {p: len(v) for p, v in partitions.items()},
               "structure_counts": {p: len(v) for p, v in STRUCTURES.items()},
               "structures": STRUCTURES, "partitions_sha256": {p: digest(v) for p, v in partitions.items()},
               "confirmation_evaluated": False, "source_book_items_used": 0,
               "source_book_explanations_used": 0, "paid_teacher_calls": 0,
               "training_target": "answer_label_only" if label_only else "derivation_and_label",
               "training_config": {"iters": 80, "batch_size": 2, "num_layers": 4,
                                   "learning_rate": 0.0001, "max_seq_length": 768,
                                   "mask_prompt": True, "seed": 41},
               "limitation": "Instances share a small number of fixed structures; no general GMAT or learner-effect claim."}
    private_json(out / "curriculum.json", summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--label-only", action="store_true")
    args = parser.parse_args()
    print(json.dumps(prepare(args.out, label_only=args.label_only)))
