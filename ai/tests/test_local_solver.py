import json

import pytest

from questionize.local_solver import answer_from, messages, prepare


def item(number=1, split="test"):
    return {"entry_id": number, "split": split, "subtype": "inference", "answer_key": "C",
            "official_explanation": "SECRET_EXPERT_TEXT", "local_reference": "SECRET_LABEL",
            "question": {"passage": "A implies B.", "stem": "What follows?",
                         "choices": [{"label": l, "text": "Option " + l, "trap": "SECRET_TRAP"} for l in "ABCDE"],
                         "hidden_key": "SECRET_KEY"}}


def test_local_prompt_excludes_all_reference_and_metadata_fields():
    for arm in ("base", "procedure", "choice"):
        encoded = json.dumps(messages(item(), arm))
        assert "SECRET" not in encoded
        assert "A implies B." in encoded
    assert len(messages(item(), "procedure")[0]["content"]) > len(messages(item())[0]["content"])


def test_local_answer_requires_explicit_unambiguous_final_label():
    assert answer_from("A and B fail.\nAnswer: C") == "C"
    assert answer_from("Answer: C\nAnswer: D") is None
    assert answer_from("A looks plausible but B fails") is None
    assert answer_from("Answer: Cat") is None


def test_local_cohort_never_samples_train_and_cannot_be_overwritten(tmp_path):
    dataset = tmp_path / "source.json"
    dataset.write_text(json.dumps({"items": [item(1, "train"), item(2), item(3, "completion_validation")]}))
    out = tmp_path / "run"
    assert prepare(dataset, out)["items"] == 2
    frozen = json.loads((out / "manifest.json").read_text())
    assert {i["entry_id"] for i in frozen["items"]} == {2, 3}
    assert frozen["scope"] == "previously_exposed_development_pilot"
    with pytest.raises(ValueError, match="already frozen"):
        prepare(dataset, out)
