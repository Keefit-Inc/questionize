import json

from questionize.local_research_worker import prepare_data
from questionize.schemas import SourceQuestion
from questionize.upload_learning import fingerprint


def test_recovered_validation_and_cross_edition_aliases_never_enter_teacher_context(tmp_path):
    items = []
    for n in range(40):
        split = "train" if n < 8 else "completion_validation" if n < 16 else "test"
        items.append({"entry_id": n, "answer_key": "A", "key_verdict": "book", "subtype": "weaken", "split": split,
            "official_explanation": f"Private source reasoning {n}",
            "question": {"passage": f"A distinct original reasoning statement {n}, since ____.",
                "stem": "Which completes the argument?" if split == "completion_validation" else "Which weakens the argument?",
                "choices": [{"label": l, "text": f"Choice {l} about situation {n}"} for l in "ABCDE"]}})
    # An old edition's training alias of a held-out question must also be excluded.
    items.append(items[8] | {"entry_id": 100, "split": "train"})
    dataset = tmp_path / "private.json"
    dataset.write_text(json.dumps({"dataset": "test-private", "items": items}))
    selected, registration, examples = prepare_data({"dataset": str(dataset), "validation_items": 16}, {"observations": [{"subtype": "weaken", "question_fingerprint": "not-a-case"}]})
    held = {fingerprint(SourceQuestion(**i["question"])) for i in items if i["split"] != "train"}
    assert len(selected) == 16
    assert sum("completes" in i.question.stem for i in selected) >= 4
    assert not set(registration["training_fingerprints"]) & held
    assert all(fingerprint(SourceQuestion(**e["question"])) not in held for e in examples)
