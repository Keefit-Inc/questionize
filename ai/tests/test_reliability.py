import copy

import pytest

from conftest import ScriptedLLM, make_question, solver
from questionize.capture_audit import issues, repair
from questionize.eval_reliability import aggregate
from questionize.integrity import integrity_issues
from questionize.pipeline import QuestionPipeline
from questionize.source_crosscheck import missing_segments


def test_repair_requires_source_review_and_preserves_parent_split():
    data = {"items": [{"entry_id": 1, "split": "test", "answer_key": "B", "number": "", "page": "2",
        "question": {"passage": "One claim. Another claim.", "stem": "The boldface means?", "choices": []}}]}
    manifest = {"parent_dataset": "v1", "parent_hash": "hash", "pdf_hash": "pdf", "patches": [
        {"entry_id": 1, "number": "1", "bold_spans": ["One claim."], "reviewed_against_scan": True}]}
    original = copy.deepcopy(data)
    fixed, audit = repair(data, manifest)
    assert data == original
    assert fixed["items"][0]["split"] == "test"
    assert fixed["items"][0]["question"]["passage"] == "[BOLD_1]One claim.[/BOLD_1] Another claim."
    assert audit["restored_emphasis_items"] == 1
    assert not audit["independent_human_review"]
    manifest["patches"][0]["reviewed_against_scan"] = False
    with pytest.raises(ValueError):
        repair(data, manifest)


def test_no_missing_or_repeated_span_is_silently_repaired():
    data = {"items": [{"entry_id": 1, "question": {"passage": "same same"}}]}
    manifest = {"patches": [{"entry_id": 1, "bold_spans": ["same"], "reviewed_against_scan": True}]}
    with pytest.raises(ValueError, match="not unique"):
        repair(data, manifest)
    assert "invalid_key" in issues({})


async def test_integrity_blocks_duplicate_answers_without_a_model_call():
    q = make_question("B").model_copy(deep=True)
    q.choices[0].text = q.choices[1].text
    llm = ScriptedLLM()
    async def emit(_):
        pass
    r = await QuestionPipeline(llm, llm, integrity_checks=True).verify(0, "", "", q, "CR", emit)
    assert not r.verification.verified
    assert r.verification.issues == ["duplicate_choice_text"]
    assert llm.calls == []


async def test_a_revision_cannot_bypass_integrity_checks():
    original = make_question("B")
    revised = original.model_copy(deep=True)
    revised.choices[0].text = revised.choices[1].text
    llm = ScriptedLLM(SolverResult=[solver("A")], Question=[revised])
    async def emit(_):
        pass
    result = await QuestionPipeline(llm, llm).verify(0, "", "", original, "CR", emit)
    assert not result.verification.verified
    assert result.verification.issues == ["duplicate_choice_text"]
    assert sum(name == "SolverResult" for name, _ in llm.calls) == 1


def test_missing_required_formatting_is_not_inferred_from_the_answer():
    q = make_question("B").model_copy(update={"stem": "The two boldfaced portions have which role?"})
    assert integrity_issues(q) == ["missing_required_emphasis"]
    q.passage = "[BOLD_1]A statement.[/BOLD_1] [BOLD_2]Then another.[/BOLD_2]"
    assert integrity_issues(q) == []


def test_metrics_distinguish_repairs_corruptions_and_errors():
    rows = [{"solver_correct": True, "legacy_correct": False, "guarded_correct": True, "judge_correct": False, "calls": 4},
            {"entry_id": 2, "error": "TimeoutError"}]
    s = aggregate("E9", rows, 2)
    assert s["legacy"]["corrupted"] == 1
    assert s["guarded"]["corrupted"] == 0
    assert s["completed"] == 1 and s["errors"] == 1
    assert s["judge"]["coverage"] == .5


def test_source_recall_detects_a_dropped_line_even_when_every_copied_word_is_correct():
    assert missing_segments("The cards request reports of fish they catch. Which helps?", "The cards request reports of fish Which helps?") == ["they catch"]
    assert missing_segments("First statement. Third statement. Second statement.", "First statement. Second statement. Third statement.") == []


def test_completion_format_requires_a_visible_blank_without_rejecting_other_stems():
    q = make_question("B").model_copy(update={"stem": "Which most logically completes the argument?", "passage": "The plan will fail, since ____."})
    assert integrity_issues(q) == []
    q.passage = "The plan will fail, since ."
    assert integrity_issues(q) == ["missing_completion_blank"]
    q.stem = "Which observation weakens the argument?"
    assert integrity_issues(q) == []


def test_recovered_records_do_not_rewrite_existing_train_test_membership():
    data = {"items": [{"entry_id": 1, "split": "test", "flags": ["not_as_printed"], "page": 1}]}
    manifest = {"patches": [{"entry_id": 1, "reviewed_against_scan": True, "resolve_flags": ["not_as_printed"], "split": "completion_validation"}]}
    with pytest.raises(ValueError, match="existing split"):
        repair(data, manifest)
