from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from conftest import ScriptedLLM, make_question, passing_critic, solver
from questionize.app import create_app
from questionize.config import ProviderConfig, Settings
from questionize.errorlog import diagnose
from questionize.pipeline import Declined, QuestionPipeline
from questionize.schemas import Choice, DiagnoseRequest, SourceQuestion, MisconceptionGuess, OptionReview, PatternObservation, PhotoReading

IMAGE = "data:image/png;base64,iVBORw0KGgo="
TRANSCRIPT = (
    "The town council claims that because the new library opened downtown, reading scores at Lincoln School rose "
    "twelve points. Which of the following, if true, most weakens the council's claim?"
)


def reading(**overrides) -> PhotoReading:
    base = PhotoReading(
        readable=True, kind="practice_question", personal_data_present=False, key_guess="C",
        question=SourceQuestion(passage=TRANSCRIPT.split("Which")[0].strip(), stem="Which" + TRANSCRIPT.split("Which")[1],
                                choices=[Choice(label=l, text=f"Printed option {l}") for l in "ABCDE"]),
        pattern=PatternObservation(
            family="CR", subtype="weaken", competency="Spot an alternative cause for a claimed effect",
            stimulus_features=["causal conclusion from one before-and-after comparison"],
            key_rule="The key names another change at the same time that could explain the effect",
            distractor_traps=["irrelevant", "too_extreme", "reversal"], difficulty_drivers=["the alternative cause is mentioned indirectly"],
            stated_level="graduate admissions",
        ),
        chosen_trap="irrelevant",
        misconception=MisconceptionGuess(mechanism_family="attention", mechanism_type="keyword_matching", statement="Picked the option that repeats the topic"),
        explanation="The right answer offers another cause for the improvement; the option chosen is on topic but does not bear on the cause.",
        difficulty=3, intent="Tests whether the learner can find a rival explanation for a claimed cause",
        learning_objectives=["Separate a correlation from its cause", "Look for a second change at the same time"],
        option_reviews=[OptionReview(label=l, trap="correct" if l == "C" else "irrelevant", reason=f"Option {l} reason in our words") for l in "EDCBA"],
    )
    return base.model_copy(update=overrides)


def pipeline_with(photo: PhotoReading) -> tuple[QuestionPipeline, ScriptedLLM]:
    primary = ScriptedLLM(PhotoReading=[photo], Question=[make_question("B")], CriticResult=[passing_critic()])
    return QuestionPipeline(primary, ScriptedLLM(SolverResult=[solver("B")])), primary


async def test_diagnosis_practice_and_observation():
    pipeline, primary = pipeline_with(reading())
    events = []

    async def emit(e):
        events.append(e)

    out = await diagnose(pipeline, DiagnoseRequest(images=[IMAGE], chosen_label="A"), emit, seed=1)

    assert primary.images == [IMAGE]
    d = out["diagnosis"]
    assert (d["chosen_correct"], d["chosen_trap"], d["misconception"]["mechanism_type"]) == (False, "irrelevant", "keyword_matching")
    assert len(out["practice"]) == 2 and all(p["verification"]["verified"] for p in out["practice"])
    assert out["leak_checks"]["passed"] and out["observation"]["subtype"] == "weaken"
    source = out.pop("source_question")
    assert "Lincoln School" in source["passage"] and len(source["choices"]) == 5, "the learner gets their question back"
    assert "Lincoln School" not in str(out), "nothing else carries the printed wording"
    writer_prompt = [u for name, u in primary.calls if name == "Question"][0]
    assert "practice_trap: irrelevant" in writer_prompt
    assert [e["stage"] for e in events][:3] == ["reading", "diagnosed", "practice"]
    assert (events[1]["difficulty"], events[1]["key_guess"], events[1]["chosen_correct"]) == (3, "C", False)
    assert (d["difficulty"], d["learning_objectives"][0]) == (3, "Separate a correlation from its cause")
    assert [r["label"] for r in d["option_reviews"]] == list("ABCDE")


async def test_reviews_that_quote_the_photo_lose_their_text_and_keep_the_design_private():
    quoting = reading()
    reviews = [r.model_copy(update={"reason": "because the new library opened downtown, reading scores at Lincoln School rose"}) if r.label == "A" else r
               for r in quoting.option_reviews]
    pipeline, _ = pipeline_with(quoting.model_copy(update={"option_reviews": reviews, "intent": TRANSCRIPT}))
    out = await diagnose(pipeline, DiagnoseRequest(images=[IMAGE], chosen_label="A"), lambda e: _noop(), seed=3)

    d = out["diagnosis"]
    assert d["intent"] == "" and d["option_reviews"][0]["reason"] == "" and d["option_reviews"][1]["reason"]
    assert out["observation"] is None, "a reader that quotes is not trusted with the commons either"


async def test_fields_that_copy_the_photo_are_blanked_and_keep_the_design_out_of_the_commons():
    leaky = reading()
    leaky = leaky.model_copy(update={"pattern": leaky.pattern.model_copy(update={"competency": "because the new library opened downtown, reading scores at Lincoln School rose twelve points"})})
    pipeline, _ = pipeline_with(leaky)
    out = await diagnose(pipeline, DiagnoseRequest(images=[IMAGE], chosen_label="C"), lambda e: _noop(), seed=2)

    assert out["diagnosis"]["competency"] == ""
    assert out["diagnosis"]["chosen_correct"] is True and out["diagnosis"]["chosen_trap"] is None
    assert out["observation"] is None and not out["leak_checks"]["passed"]


async def _noop():
    return None


@pytest.mark.parametrize("kind,reason", [("live_exam_suspected", "live_exam"), ("not_a_question", "not_a_question")])
async def test_live_exam_content_and_non_questions_are_declined(kind, reason):
    pipeline, primary = pipeline_with(reading(kind=kind))
    with pytest.raises(Declined) as exc:
        await diagnose(pipeline, DiagnoseRequest(images=[IMAGE]), lambda e: _noop())
    assert exc.value.reason == reason
    assert [name for name, _ in primary.calls] == ["PhotoReading"]


def test_diagnose_endpoint_accepts_only_image_data_urls():
    p = ProviderConfig("meta", "http://x", "k", "m")
    client = TestClient(create_app(Settings(primary=p, solver=p, internal_token="t"), pipeline_with(reading())[0]))
    headers = {"X-Internal-Token": "t"}
    assert client.post("/v1/diagnose", json={"images": ["https://example.com/x.png"]}, headers=headers).status_code == 422
    assert client.post("/v1/diagnose", json={"images": [IMAGE] * 4}, headers=headers).status_code == 422
    r = client.post("/v1/diagnose", json={"images": [IMAGE, IMAGE], "chosen_label": "A"}, headers=headers)
    assert r.status_code == 200
    assert '"stage": "diagnosis"' in r.text
