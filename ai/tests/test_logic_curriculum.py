from itertools import product
import json

import pytest

from questionize.logic_curriculum import STRUCTURES, exercise, holds, prepare


def independent_value(expr, world):
    if isinstance(expr, int):
        return world[expr]
    op, *args = expr
    values = [independent_value(a, world) for a in args]
    return {"not": lambda: not values[0], "and": lambda: False not in values,
            "or": lambda: True in values, "implies": lambda: (not values[0]) or values[1]}[op]()


def test_all_structure_keys_unique_and_distractors_have_counterexamples():
    for names in STRUCTURES.values():
        for name in names:
            for seed in range(5):
                item = exercise(name, seed, seed)
                ref = item["reference"]
                worlds = [w for w in product((False, True), repeat=4)
                          if all(independent_value(p, w) for p in ref["premises"])]
                assert worlds
                truth = [all(independent_value(c, w) for w in worlds) for c in ref["options"]]
                assert sum(truth) == 1
                assert chr(65 + truth.index(True)) == item["answer_key"]
                for w in worlds:
                    assert all(holds(p, w) == independent_value(p, w) for p in ref["premises"])


def test_curriculum_uses_disjoint_structures_and_no_confirmation_in_training(tmp_path):
    out = tmp_path / "curriculum"
    summary = prepare(out, instances=3)
    assert summary["source_book_items_used"] == 0
    train = set(STRUCTURES["train"])
    dev = set(STRUCTURES["development"])
    confirmation = set(STRUCTURES["confirmation"])
    assert not train & dev and not train & confirmation and not dev & confirmation
    assert len((out / "train.jsonl").read_text().splitlines()) == 12
    assert not (out / "test.jsonl").exists()
    assert summary["confirmation_evaluated"] is False
    manifest = json.loads((out / "development" / "manifest.json").read_text())
    assert {i["structure_group"] for i in manifest["items"]} == dev
    with pytest.raises(ValueError, match="never overwrite"):
        prepare(out)


def test_choice_training_matches_the_format_neutral_evaluation_prompt(tmp_path):
    from questionize.local_solver import CHOICE_SYSTEM
    out = tmp_path / "choice"
    summary = prepare(out, instances=2, label_only=True)
    assert summary["training_target"] == "answer_label_only"
    for line in (out / "train.jsonl").read_text().splitlines():
        chat = json.loads(line)["messages"]
        assert chat[0]["content"] == CHOICE_SYSTEM
        assert chat[-1]["content"] in "ABCDE"
