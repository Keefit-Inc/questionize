import json
import pytest

from conftest import ScriptedLLM, solver
from test_errorlog import IMAGE, reading
from questionize.evolution import content_hash
from questionize.schemas import DiagnoseRequest, FlatPhotoReading, LearningMemory, SourceQuestion, Choice
from questionize.pipeline import QuestionPipeline
from questionize.upload_learning import Capture, UploadAnalysis, read_and_assess, solver_prompt, fingerprint, canonical_subtype, explanation_contract


def capture(**changes):
    values = dict(readable=True, family="CR", passage="A report attributes a change to a new policy.",
        stem="Which observation weakens that attribution?", printed_key="B", reference_explanation="PRIVATE_REFERENCE_EXPLANATION",
        **{f"option_{l.lower()}": f"Distinct printed option {l}" for l in "ABCDE"})
    return Capture(**(values | changes))


def memory():
    payload = {"expert_rules": ["Check for alternative causes."], "experience_rules": []}
    return LearningMemory(id="memory-test", version=2, hash=content_hash(payload), payload=payload)


async def emit(_):
    pass


async def test_reference_and_images_are_withheld_from_both_independent_solver_calls():
    main = ScriptedLLM(Capture=[capture()], SolverResult=[solver("C")], UploadAnalysis=[UploadAnalysis.model_validate(FlatPhotoReading.from_reading(reading()).model_dump())])
    control = ScriptedLLM(model="control", SolverResult=[solver("B")])
    result = await read_and_assess(QuestionPipeline(main, control), DiagnoseRequest(images=[IMAGE], answer_key="B", source_attested=True, learning_policy=memory()), emit)
    _, _, observation, trace, reference_text = result
    assert observation["outcome"] == "reference_mismatch"
    assert observation["reference_status"] == "confirmed_reference"
    assert observation["measurements"]["main_matches_reference"] is False
    assert observation["measurements"]["control_matches_reference"] is True
    assert trace["policy_hash"] == memory().hash
    for model in [main, control]:
        prompt = next(text for schema, text in model.calls if schema == "SolverResult")
        assert "PRIVATE_REFERENCE_EXPLANATION" not in prompt
        assert "printed_key" not in prompt and "reference_key" not in prompt and IMAGE not in prompt
    assert reference_text == "PRIVATE_REFERENCE_EXPLANATION"
    assert "PRIVATE_REFERENCE_EXPLANATION" not in json.dumps(observation)


async def test_ai_agreement_never_becomes_a_confirmed_reference():
    main = ScriptedLLM(Capture=[capture(printed_key=None, reference_explanation="")], SolverResult=[solver("B")], UploadAnalysis=[UploadAnalysis.model_validate(FlatPhotoReading.from_reading(reading()).model_dump())])
    control = ScriptedLLM(SolverResult=[solver("B")])
    _, _, observation, trace, _ = await read_and_assess(QuestionPipeline(main, control), DiagnoseRequest(images=[IMAGE]), emit)
    assert observation["reference_status"] == "ai_estimated"
    assert observation["outcome"] == "ai_agreement"
    assert observation["measurements"]["main_matches_reference"] is None


async def test_conflicting_printed_and_entered_keys_are_not_promoted_by_curator_attestation():
    main = ScriptedLLM(Capture=[capture(printed_key="A")], SolverResult=[solver("B")], UploadAnalysis=[UploadAnalysis.model_validate(FlatPhotoReading.from_reading(reading()).model_dump())])
    control = ScriptedLLM(SolverResult=[solver("B")])
    r, _, observation, _, _ = await read_and_assess(QuestionPipeline(main, control), DiagnoseRequest(images=[IMAGE], answer_key="B", source_attested=True), emit)
    assert observation["reference_status"] == "disputed"
    assert r.key_guess is None


def test_local_reference_is_never_serialized_into_blind_prompt_and_option_permutations_share_a_group():
    q = SourceQuestion(passage="A statement.", stem="Which follows?", choices=[Choice(label=l,text=f"Option {l}") for l in "ABCDE"], local_reference={"key":"A", "explanation":"SECRET"})
    system, user = solver_prompt(q, memory())
    assert "SECRET" not in system + user and "local_reference" not in user
    q2 = q.model_copy(deep=True)
    q2.choices = list(reversed(q2.choices))
    assert fingerprint(q) == fingerprint(q2)


def test_subtype_spelling_does_not_silently_break_expert_example_retrieval():
    assert canonical_subtype("Inference") == "inference"
    assert canonical_subtype("Must be true") == "inference"
    assert canonical_subtype("Bold Face") == "structure"
    assert canonical_subtype("") == "unknown"


def test_an_explanation_for_another_answer_cannot_be_silently_relabelled():
    corrected, issue = explanation_contract(reading(), "B", "confirmed_reference")
    assert corrected.key_guess == "B"
    assert issue == "answer_explanation_conflict"
    assert corrected.option_reviews == [] and corrected.misconception is None
    assert "withheld" in corrected.explanation


def test_unresolved_evidence_cannot_identify_a_correct_option_or_learner_misconception():
    uncertain, issue = explanation_contract(reading(), None, "disputed")
    assert uncertain.key_guess is None and not uncertain.option_reviews
    assert uncertain.chosen_trap is None and uncertain.misconception is None
    assert issue == "unresolved_reference"
    estimated, issue = explanation_contract(reading(), "C", "ai_estimated")
    assert estimated.explanation.startswith("AI estimate")
    assert estimated.misconception is None and issue is None


async def test_failed_detailed_analysis_preserves_capture_and_independent_results():
    def unavailable():
        raise TimeoutError("analyst unavailable")
    main = ScriptedLLM(Capture=[capture()], SolverResult=[solver("B")], UploadAnalysis=[unavailable])
    control = ScriptedLLM(SolverResult=[solver("B")])
    r, _, observation, trace, _ = await read_and_assess(QuestionPipeline(main, control), DiagnoseRequest(images=[IMAGE]), emit)
    assert r.question.passage == capture().passage
    assert r.key_guess == "B" and r.option_reviews == []
    assert observation["outcome"] == "reference_match"
    assert trace["detailed_explanation_available"] is False


def test_analysis_schema_cannot_replace_or_retranscribe_the_captured_question():
    assert not {"passage", "stem", "option_a", "readable", "personal_data_present"} & UploadAnalysis.model_fields.keys()
