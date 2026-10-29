import asyncio
import json

from conftest import ScriptedLLM, solver

from questionize import eval_e1, eval_e4, memory
from questionize.eval_e1 import DatasetItem, Explanation, load_baseline, summarize


def item(number="1", passage="Accidents fell after bike lanes opened on Main Street.", key="B", **over):
    choices = [{"label": label, "text": f"Option {label} on the lanes."} for label in "ABCDE"]
    base = {"entry_id": int(number), "number": number, "page": number, "answer_key": key, "subtype": "weaken",
            "question": {"passage": passage, "stem": "Which most weakens it?", "choices": choices},
            "official_explanation": "Speed cameras offer another cause for the fall in accidents.", "flags": [], "flagged": False}
    return base | over


def test_e4_agreement_flags_differences_and_splits_the_rest():
    rules = [item("1"), item("2"), item("3")]
    model = [item("1"), item("2", passage="Crashes dropped sharply after protected lanes opened downtown."), item("3", key="C"), item("4")]
    merged, summary = eval_e4.compare(rules, model, "official-cr-v1")
    flags = {i["number"]: i["flags"] for i in merged}
    assert flags["1"] == [] and flags["2"] == ["rules_vs_model:passage"] and flags["3"] == ["rules_vs_model:key"]
    assert flags["4"] == ["no_rules_match"]
    assert summary["R_vs_Mtext"]["primary"] == round(1 / 3, 4) and summary["counts"]["matched"] == 3
    assert merged[0]["split"] in ("train", "test") and merged[1]["split"] == ""
    # The split is a pure function of dataset and number: stable across reruns.
    assert eval_e4.split_of("official-cr-v1", "1") == eval_e4.split_of("official-cr-v1", "1")
    shares = [eval_e4.split_of("d", str(n)) for n in range(1000)]
    assert 0.35 < shares.count("test") / 1000 < 0.45


def test_memory_learns_rules_and_drops_copied_lessons():
    copied = memory.Lesson(lesson="Speed cameras offer another cause for the fall in accidents here.", from_mistake=True)
    good = memory.Lesson(lesson="Before choosing, name the gap between evidence and conclusion; prefer the option that opens another cause.", from_mistake=True)
    model = ScriptedLLM(
        SolverResult=[solver("A"), solver("B")],
        Lesson=[copied, good],
        Playbook=[memory.Playbook(rules=["Name the gap first; a weakener supplies another cause."])],
    )
    items = [DatasetItem.model_validate(item("1")), DatasetItem.model_validate(item("2"))]
    learned, stats = asyncio.run(memory.learn(model, items, concurrency=1))
    assert learned == {"weaken": ["Name the gap first; a weakener supplies another cause."]}
    assert stats == {"items": 2, "solved_correctly": 1, "lessons": 1, "dropped_for_copying": 1}
    # The model saw the key and the book's explanation only after answering blind.
    assert "BOOK'S KEY: B" in model.calls[1][1] and "BOOK'S KEY" not in model.calls[0][1]


def test_e1_with_memory_puts_lessons_in_prompts_and_pairs_with_the_baseline(tmp_path):
    items = [DatasetItem.model_validate(item(str(n))) for n in (1, 2)]
    model = ScriptedLLM(
        model="m",
        AnswerAndExplanation=[eval_e1.AnswerAndExplanation(answer_label="B", confidence=0.9, explanation="x")],
        Explanation=[Explanation(explanation="x")],
    )
    seen = []
    original = model.complete

    async def spy(system, user, schema, **kw):
        seen.append(system)
        return await original(system, user, schema, **kw)

    model.complete = spy
    outcomes = asyncio.run(eval_e1.run(items, ["B0"], model, model, None, memory={"weaken": ["Name the gap first."]}))
    assert {o.condition for o in outcomes} == {"B0+M"} and all("Name the gap first." in s for s in seen)

    base = tmp_path / "base"
    base.mkdir()
    (base / "results.jsonl").write_text("\n".join(json.dumps({"condition": "B0", "entry_id": n, "correct": False}) for n in (1, 2)))
    summary = summarize(outcomes, baseline=load_baseline(base))
    assert summary["B0+M"]["vs_baseline"]["b"] == 2 and summary["B0+M"]["vs_baseline"]["baseline_accuracy"] == 0.0
