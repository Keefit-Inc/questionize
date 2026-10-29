import asyncio
import csv
import json
import re

from conftest import ScriptedLLM, solver

from questionize import eval_e1
from questionize.eval_e1 import (
    AnswerAndExplanation,
    DatasetItem,
    Explanation,
    mcnemar,
    summarize,
    wilson,
)
from questionize.judge import ArgumentJudge
from questionize.schemas import JudgeRatings, OptionRating

CHOICES = [
    {"label": "A", "text": "Bike sales rose."},
    {"label": "B", "text": "Speed cameras were installed the same year."},
    {"label": "C", "text": "The lanes are painted green."},
    {"label": "D", "text": "Other cities built lanes."},
    {"label": "E", "text": "Some drivers dislike the lanes."},
]


def item(entry_id=1, key="B", subtype="weaken", verdict="agrees"):
    return DatasetItem.model_validate(
        {
            "entry_id": entry_id,
            "answer_key": key,
            "key_verdict": verdict,
            "subtype": subtype,
            "question": {"passage": "Accidents fell after bike lanes opened.", "stem": "Which most weakens the argument?", "choices": CHOICES},
        }
    )


class TextJudge:
    """Rates the speed-camera option as the strongest weakener."""

    model = "judge"

    async def complete(self, system, user, schema, *, temperature=0.4, images=None):
        return JudgeRatings(
            ratings=[
                OptionRating(option=letter, support_delta=-0.8 if "Speed cameras" in text else 0.0, necessity=0.1)
                for letter, text in re.findall(r"^\(([A-H])\) (.+)$", user, re.MULTILINE)
            ]
        )


def explainer():
    return Explanation(explanation="B gives another cause.")


def test_b0_scores_against_the_key():
    primary = ScriptedLLM(AnswerAndExplanation=[AnswerAndExplanation(answer_label="B", confidence=0.8, explanation="x")])
    out = asyncio.run(eval_e1.run_b0(primary, item()))
    assert out.correct and out.calls == 1


def test_b1_judge_overrides_an_unstable_solver():
    primary = ScriptedLLM(Explanation=[explainer()])
    wrong = ScriptedLLM(model="solver", SolverResult=[solver("A", 0.6)])
    judge = ArgumentJudge([TextJudge()], samples_per_judge=4, seed=1)
    out = asyncio.run(eval_e1.run_b1(primary, wrong, judge, item(), eval_e1.random.Random(1)))
    assert out.answer == "B" and out.notes["judge_override"] and out.notes["solver"] == "A"
    # The explainer is told the settled answer, not asked to pick one.
    assert "SETTLED ANSWER: B" in primary.calls[0][1]


def test_b1_without_a_measure_keeps_the_solver():
    primary = ScriptedLLM(Explanation=[explainer()])
    out = asyncio.run(eval_e1.run_b1(primary, ScriptedLLM(SolverResult=[solver("C")]), ArgumentJudge([TextJudge()]), item(subtype="flaw"), eval_e1.random.Random(1)))
    assert out.answer == "C" and "judge_top" not in out.notes


def test_b2_debates_only_on_disagreement():
    a = ScriptedLLM(model="a", SolverResult=[solver("A", 0.6), solver("B", 0.7)], Explanation=[explainer()])
    b = ScriptedLLM(model="b", SolverResult=[solver("B", 0.9), solver("B", 0.9)])
    out = asyncio.run(eval_e1.run_b2(a, b, item(), "B2"))
    assert out.answer == "B" and out.notes["agreed"] and out.notes["round2"] == ["B", "B"] and out.calls == 5

    agree_a = ScriptedLLM(model="a", SolverResult=[solver("B")], Explanation=[explainer()])
    agree_b = ScriptedLLM(model="b", SolverResult=[solver("B")])
    out = asyncio.run(eval_e1.run_b2(agree_a, agree_b, item(), "B2"))
    assert "round2" not in out.notes and out.calls == 3


def test_statistics():
    assert wilson(0, 0) == (0.0, 0.0)
    low, high = wilson(8, 10)
    assert 0.49 < low < 0.5 and 0.94 < high < 0.95
    # 6 discordant pairs all one way: exact two-sided p = 2 / 64.
    base = {i: False for i in range(6)} | {6: True}
    other = {i: True for i in range(7)}
    assert mcnemar(base, other) == {"b": 6, "c": 0, "p": 0.0312}


def test_run_summarizes_and_labels_same_model_debate():
    model = ScriptedLLM(
        model="same",
        AnswerAndExplanation=[AnswerAndExplanation(answer_label="A", confidence=0.5, explanation="x")],
        SolverResult=[solver("B")],
        Explanation=[explainer()],
        JudgeRatings=[JudgeRatings(ratings=[OptionRating(option=l, support_delta=0.0, necessity=0.1) for l in "ABCDE"])],
    )
    items = [item(1), item(2)]
    outcomes = asyncio.run(eval_e1.run(items, ["B0", "B2"], model, model, None))
    summary = summarize(outcomes)
    assert set(summary) == {"B0", "B2'"}
    assert summary["B0"]["accuracy"] == 0.0 and summary["B2'"]["accuracy"] == 1.0
    assert summary["B2'"]["vs_B0"]["b"] == 2 and summary["B2'"]["vs_B0"]["diff_ci95"] == (1.0, 1.0)


def test_main_writes_run_files_and_a_text_free_ledger_line(tmp_path, monkeypatch):
    dataset = tmp_path / "official.json"
    raw = [i.model_dump() for i in (item(1), item(2, verdict="disputed"))] + [item(3).model_dump() | {"answer_key": None}]
    dataset.write_text(json.dumps({"dataset": "official-cr-v1", "items": raw}))

    model = ScriptedLLM(model="same", AnswerAndExplanation=[AnswerAndExplanation(answer_label="B", confidence=0.9, explanation="Because.")])
    monkeypatch.setenv("LLM_PROVIDER", "meta")
    monkeypatch.setattr("questionize.llm.make_llm", lambda provider, timeout: model)
    ledger = tmp_path / "ledger.jsonl"
    eval_e1.main([str(dataset), "--conditions", "B0", "--out", str(tmp_path / "runs"), "--ledger", str(ledger)])

    (run_dir,) = (tmp_path / "runs").iterdir()
    manifest = json.loads((run_dir / "manifest.json").read_text())
    assert manifest["n_items"] == 1 and manifest["excluded"] == {"no_key": 1, "disputed_key": 1}
    sheet = list(csv.reader((run_dir / "rating_sheet.csv").open()))
    assert len(sheet) == 2 and "condition" not in sheet[0]
    line = json.loads(ledger.read_text())
    assert line["summary"]["B0"]["accuracy"] == 1.0
    assert "Accidents fell" not in ledger.read_text() and str(tmp_path) not in ledger.read_text()
