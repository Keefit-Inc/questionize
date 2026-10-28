from __future__ import annotations

import pytest

from conftest import ARTICLE, ScriptedLLM, make_analysis, make_question, passing_critic, solver
from questionize.pipeline import ArticleDeclined, QuestionPipeline, longest_copied_run, normalize_question
from questionize.schemas import CriticResult, GenerateRequest


def req(**kw) -> GenerateRequest:
    return GenerateRequest(text=ARTICLE, title="Bike lanes", types=kw.pop("types", ["CR"]), **kw)


async def test_verified_on_first_pass():
    primary = ScriptedLLM(
        ArticleAnalysis=[make_analysis()], Question=[make_question("B")], CriticResult=[passing_critic()]
    )
    blind = ScriptedLLM(model="solver-model", SolverResult=[solver("B")])
    events = []

    async def emit(e):
        events.append(e)

    out = await QuestionPipeline(primary, blind, seed=1).run(req(), emit)

    assert len(out.questions) == 1
    vq = out.questions[0]
    assert vq.verification.verified and vq.verification.attempts == 1
    assert vq.verification.solver_model == "solver-model"
    assert [c.label for c in vq.question.choices] == list("ABCDE")
    assert [e["stage"] for e in events][:3] == ["analyze", "analyzed", "plan"]
    assert events[-1]["stage"] == "question"


async def test_solver_never_sees_answer_key():
    q = make_question("B")
    q = q.model_copy(update={"explanation": "SECRET-EXPLANATION"})
    primary = ScriptedLLM(ArticleAnalysis=[make_analysis()], Question=[q], CriticResult=[passing_critic()])
    blind = ScriptedLLM(SolverResult=[solver("B")])
    await QuestionPipeline(primary, blind).run(req())
    solver_prompt = blind.calls[0][1]
    assert "SECRET-EXPLANATION" not in solver_prompt
    assert "correct_label" not in solver_prompt


async def test_disagreement_triggers_revision_then_passes():
    primary = ScriptedLLM(
        ArticleAnalysis=[make_analysis()],
        Question=[make_question("B"), make_question("C")],
        CriticResult=[passing_critic()],
    )
    blind = ScriptedLLM(SolverResult=[solver("D"), solver("C")])
    out = await QuestionPipeline(primary, blind, max_revisions=2).run(req())
    v = out.questions[0].verification
    assert v.verified and v.attempts == 2
    # Critic is skipped when the solver disagrees, so it runs only once.
    assert sum(1 for name, _ in primary.calls if name == "CriticResult") == 1


async def test_gives_up_after_max_revisions_and_marks_unverified():
    bad_critic = CriticResult(
        verdict="revise",
        unique_answer=False,
        faithful_to_source=True,
        distractor_quality=2,
        issues=["Option D is also defensible"],
        revision_guidance="Narrow option D",
    )
    primary = ScriptedLLM(ArticleAnalysis=[make_analysis()], Question=[make_question("B")], CriticResult=[bad_critic])
    blind = ScriptedLLM(SolverResult=[solver("B")])
    out = await QuestionPipeline(primary, blind, max_revisions=1).run(req())
    v = out.questions[0].verification
    assert not v.verified and v.attempts == 2
    assert v.issues == ["Option D is also defensible"]


async def test_multiple_types_and_counts_run_in_parallel():
    primary = ScriptedLLM(
        ArticleAnalysis=[make_analysis()], Question=[lambda: make_question("B")], CriticResult=[passing_critic()]
    )
    blind = ScriptedLLM(SolverResult=[solver("B")])
    out = await QuestionPipeline(primary, blind).run(req(types=["RC", "CR", "SC"], count_per_type=2))
    assert [q.question.type for q in out.questions] == ["RC", "RC", "CR", "CR", "SC", "SC"]


def test_longest_copied_run_finds_shared_words():
    article = "The mayor concluded that expanding bike lanes citywide will make all streets safer."
    n, text = longest_copied_run("Officials say expanding bike lanes citywide will help.", article)
    assert (n, text) == (5, "expanding bike lanes citywide will")
    assert longest_copied_run("Nothing in common here.", article) == (0, "")


async def test_copied_passage_is_rewritten_before_solving():
    copied = make_question("B").model_copy(update={"passage": ARTICLE[:400]})
    primary = ScriptedLLM(
        ArticleAnalysis=[make_analysis()], Question=[copied, make_question("B")], CriticResult=[passing_critic()]
    )
    blind = ScriptedLLM(SolverResult=[solver("B")])
    events = []

    async def emit(e):
        events.append(e)

    out = await QuestionPipeline(primary, blind, max_copied_words=12).run(req(), emit)

    v = out.questions[0].verification
    assert v.verified and v.attempts == 2 and v.copied_words <= 12
    # The solver only ever saw the rewritten passage.
    assert len(blind.calls) == 1
    reviser_prompt = [u for name, u in primary.calls if name == "Question"][1]
    assert "copied_from_article" in reviser_prompt
    assert any("copies" in e.get("message", "") for e in events if e["stage"] == "verdict")


async def test_passage_that_keeps_copying_ships_unverified():
    copied = make_question("B").model_copy(update={"passage": ARTICLE[:400]})
    primary = ScriptedLLM(ArticleAnalysis=[make_analysis()], Question=[copied])
    blind = ScriptedLLM(SolverResult=[solver("B")])
    out = await QuestionPipeline(primary, blind, max_revisions=1).run(req())
    v = out.questions[0].verification
    assert not v.verified and v.copied_words > 12 and v.solver_answer == ""
    assert "consecutive words" in v.issues[0]
    assert blind.calls == []


def test_trap_tags_follow_the_key():
    q = make_question("B")
    rationales = [r.model_copy(update={"trap": "correct" if r.label == "D" else "too_extreme"}) for r in q.choice_rationales]
    fixed = normalize_question(q.model_copy(update={"choice_rationales": rationales}), "CR")
    traps = {r.label: r.trap for r in fixed.choice_rationales}
    assert traps["B"] == "correct"
    assert traps["D"] == "unsupported"
    assert [t for t in traps.values()].count("correct") == 1


async def test_content_flags_reach_the_result():
    flagged = make_analysis().model_copy(update={"content_flags": ["sexual_violence"]})
    primary = ScriptedLLM(ArticleAnalysis=[flagged], Question=[make_question("B")], CriticResult=[passing_critic()])
    out = await QuestionPipeline(primary, ScriptedLLM(SolverResult=[solver("B")])).run(req())
    assert out.analysis.content_flags == ["sexual_violence"]


async def test_unsuitable_page_stops_before_writing():
    thin = make_analysis().model_copy(
        update={"suitability": "exam_material", "suitability_reason": "This page is a set of practice exam questions."}
    )
    primary = ScriptedLLM(ArticleAnalysis=[thin])
    blind = ScriptedLLM()
    with pytest.raises(ArticleDeclined) as exc:
        await QuestionPipeline(primary, blind).run(req())
    assert exc.value.reason == "exam_material"
    assert [name for name, _ in primary.calls] == ["ArticleAnalysis"]
    assert blind.calls == []
