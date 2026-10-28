from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from conftest import ARTICLE, FakeJudgeLLM, ScriptedLLM, flat_scores, make_analysis, make_question, passing_critic, solver
from questionize.app import create_app
from questionize.config import ProviderConfig, Settings
from questionize.judge import ArgumentJudge
from questionize.pipeline import QuestionPipeline
from questionize.schemas import GenerateRequest


def weaken_item(correct: str = "B", passage: str | None = None):
    q = make_question(correct)  # sub-type "weaken"
    return q.model_copy(update={"passage": passage}) if passage else q


async def test_clear_key_passes_and_options_map_back_through_the_shuffle():
    judge = ArgumentJudge([FakeJudgeLLM(flat_scores(B=(-0.8, 0.2), D=(0.3, 0.1)))], samples_per_judge=4, seed=7)
    result = await judge.judge(weaken_item("B"))

    assert result.verdict == "pass"
    assert result.measure == "support_delta" and result.direction == "min"
    assert result.key_first_rate == 1.0
    assert abs(result.margin - 0.8) < 1e-9
    by_label = {o.label: o for o in result.options}
    assert by_label["B"].support_delta.value == -0.8
    assert by_label["D"].support_delta.value == 0.3
    assert result.samples == 4


async def test_close_call_takes_more_samples_then_reports_ambiguous():
    model = FakeJudgeLLM(flat_scores(B=(-0.5, 0.2), C=(-0.45, 0.2)))
    judge = ArgumentJudge([model], samples_per_judge=3, min_margin=0.15, seed=1)
    result = await judge.judge(weaken_item("B"))

    assert result.verdict == "ambiguous"
    assert result.runner_up == "C"
    assert model.calls == 6  # one extra round before deciding


async def test_another_option_beating_the_key_is_a_wrong_key():
    judge = ArgumentJudge([FakeJudgeLLM(flat_scores(B=(-0.2, 0.2), E=(-0.9, 0.1)))], seed=3)
    result = await judge.judge(weaken_item("B"))
    assert result.verdict == "wrong_key"
    assert result.runner_up == "E"


async def test_assumption_items_are_decided_by_necessity():
    q = make_question("C").model_copy(update={"subtype": "assumption"})
    # D strengthens more, but only C is required: the classic strengthener-posing-as-assumption trap.
    judge = ArgumentJudge([FakeJudgeLLM(flat_scores(C=(0.3, 0.9), D=(0.7, 0.2)))], seed=5)
    result = await judge.judge(q)
    assert result.measure == "necessity"
    assert result.verdict == "pass"


async def test_uncovered_subtypes_are_measured_but_not_gated():
    q = make_question("B").model_copy(update={"subtype": "flaw"})
    result = await ArgumentJudge([FakeJudgeLLM(flat_scores())], seed=2).judge(q)
    assert result.verdict == "not_applicable"
    assert len(result.options) == 5


def test_the_same_model_twice_counts_once():
    a, b = FakeJudgeLLM(flat_scores(), model="m"), FakeJudgeLLM(flat_scores(), model="m")
    assert len(ArgumentJudge([a, b]).judges) == 1
    assert ArgumentJudge([a, FakeJudgeLLM(flat_scores(), model="n")]).version == "aj-0.1:m+n"


async def test_pipeline_revises_an_item_the_judge_finds_ambiguous():
    first = weaken_item("B", passage="FIRST draft: accidents fell after bike lanes, so lanes make streets safe.")
    second = weaken_item("B", passage="SECOND draft: accidents fell after bike lanes, so lanes make streets safe.")

    def scores(passage):
        if passage.startswith("FIRST"):
            return flat_scores(B=(-0.5, 0.2), C=(-0.48, 0.2))
        return flat_scores(B=(-0.8, 0.2))

    primary = ScriptedLLM(ArticleAnalysis=[make_analysis()], Question=[first, second], CriticResult=[passing_critic()])
    blind = ScriptedLLM(model="solver-model", SolverResult=[solver("B")])
    judge = ArgumentJudge([FakeJudgeLLM(scores)], samples_per_judge=3, seed=11)
    events = []

    async def emit(e):
        events.append(e)

    out = await QuestionPipeline(primary, blind, judge=judge).run(GenerateRequest(text=ARTICLE, types=["CR"]), emit)

    vq = out.questions[0]
    assert vq.verification.verified and vq.verification.attempts == 2
    assert vq.judge is not None and vq.judge.verdict == "pass"
    reviser_prompt = [u for name, u in primary.calls if name == "Question"][1]
    assert "argument_judge" in reviser_prompt
    verdicts = [e for e in events if e["stage"] == "verdict"]
    assert verdicts[0]["passed"] is False and verdicts[0]["judge"]["verdict"] == "ambiguous"
    assert verdicts[1]["judge"]["verdict"] == "pass"


def test_judge_endpoint():
    p = ProviderConfig("meta", "http://x", "k", "m")
    judge = ArgumentJudge([FakeJudgeLLM(flat_scores(B=(-0.8, 0.2)))], seed=4)
    app = create_app(Settings(primary=p, solver=p, internal_token="t"), QuestionPipeline(ScriptedLLM(), ScriptedLLM(), judge=judge))
    q = weaken_item("B")
    body = {"passage": q.passage, "stem": q.stem, "choices": [c.model_dump() for c in q.choices], "correct_label": "B", "subtype": "weaken"}

    client = TestClient(app)
    assert client.post("/v1/judge", json=body).status_code == 401
    r = client.post("/v1/judge", json=body, headers={"X-Internal-Token": "t"})
    assert r.status_code == 200
    assert r.json()["verdict"] == "pass"

    no_judge = create_app(Settings(primary=p, solver=p, internal_token="t"), QuestionPipeline(ScriptedLLM(), ScriptedLLM()))
    assert TestClient(no_judge).post("/v1/judge", json=body, headers={"X-Internal-Token": "t"}).status_code == 503


async def test_eval_scores_accuracy_and_calibration(tmp_path):
    from questionize.eval_judge import evaluate, expected_calibration_error, load_gold

    example = (Path(__file__).resolve().parents[1] / "eval" / "gold.example.jsonl").read_text().strip()
    wrong = example.replace('"example-weaken-1"', '"example-weaken-2"').replace('"gold_label": "B"', '"gold_label": "D"')
    skipped = example.replace('"example-weaken-1"', '"example-flaw"').replace('"subtype": "weaken"', '"subtype": "flaw"')
    gold = tmp_path / "gold.jsonl"
    gold.write_text("\n".join([example, wrong, skipped]) + "\n")

    class TextJudge(FakeJudgeLLM):
        """Rates the alternative-cause option (B in the example) as the strongest weakener."""

        async def complete(self, system, user, schema, *, temperature=0.4):
            import re

            from questionize.schemas import JudgeRatings, OptionRating

            self.calls += 1
            ratings = [
                OptionRating(option=letter, support_delta=-0.8 if "speed cameras" in text else 0.0, necessity=0.1)
                for letter, text in re.findall(r"^\(([A-E])\) (.+)$", user, re.M)
            ]
            return JudgeRatings(ratings=ratings)

    report = await evaluate(ArgumentJudge([TextJudge({})], seed=9), load_gold(gold))
    assert report["items"] == 3 and report["scored"] == 2
    assert report["accuracy"] == 0.5
    rows = {r["id"]: r for r in report["rows"]}
    assert rows["example-weaken-1"]["correct"] and rows["example-weaken-1"]["verdict"] == "pass"
    assert rows["example-weaken-2"]["predicted"] == "B" and not rows["example-weaken-2"]["correct"]
    assert "skipped" in rows["example-flaw"]
    assert expected_calibration_error([(1.0, True), (1.0, False)]) == 0.5
