from __future__ import annotations

from fastapi.testclient import TestClient

from conftest import FakeJudgeLLM, ScriptedLLM, flat_scores, make_question, passing_critic, solver
from questionize.app import create_app
from questionize.config import ProviderConfig, Settings
from questionize.judge import ArgumentJudge
from questionize.pipeline import QuestionPipeline
from questionize.reviewer import review
from questionize.schemas import CrowdStats, Flag, ReviewDecision, ReviewRequest


def request() -> ReviewRequest:
    return ReviewRequest(
        question=make_question("B"),
        flags=[Flag(reason="two_answers", comment="D also weakens it")] * 3,
        crowd=CrowdStats(attempts=40, tally={"A": 2, "B": 15, "C": 1, "D": 21, "E": 1}, strong_top_choice="D", strong_top_share=0.55),
    )


def decision(verdict: str) -> ReviewDecision:
    return ReviewDecision(verdict=verdict, findings=["D is also defensible"], revision_guidance="Make D clearly irrelevant")


async def test_keep_returns_the_decision_and_the_judge_without_rewriting():
    primary = ScriptedLLM(ReviewDecision=[decision("keep")])
    judge = ArgumentJudge([FakeJudgeLLM(flat_scores(B=(-0.8, 0.2)))], seed=2)
    result = await review(QuestionPipeline(primary, ScriptedLLM(), judge=judge), request())

    assert result.decision.verdict == "keep"
    assert result.judge is not None and result.judge.verdict == "pass"
    assert result.revised is None
    reviewer_prompt = primary.calls[0][1]
    assert "two_answers" in reviewer_prompt and "strong_top_choice" in reviewer_prompt


async def test_revise_rewrites_with_findings_then_verifies_the_revision():
    fixed = make_question("B").model_copy(update={"stem": "Revised stem: which most seriously weakens the argument?"})
    primary = ScriptedLLM(ReviewDecision=[decision("revise")], Question=[fixed], CriticResult=[passing_critic()])
    blind = ScriptedLLM(model="solver-model", SolverResult=[solver("B")])
    judge = ArgumentJudge([FakeJudgeLLM(flat_scores(B=(-0.8, 0.2)))], seed=4)

    result = await review(QuestionPipeline(primary, blind, judge=judge), request())

    assert result.decision.verdict == "revise"
    assert result.revised is not None and result.revised.verification.verified
    assert result.revised.question.stem.startswith("Revised stem")
    reviser_prompt = [u for name, u in primary.calls if name == "Question"][0]
    assert "reviewer_findings" in reviser_prompt and "Make D clearly irrelevant" in reviser_prompt


def test_review_endpoint_requires_the_token():
    p = ProviderConfig("meta", "http://x", "k", "m")
    pipeline = QuestionPipeline(ScriptedLLM(ReviewDecision=[decision("retire")]), ScriptedLLM())
    client = TestClient(create_app(Settings(primary=p, solver=p, internal_token="t"), pipeline))
    body = request().model_dump()
    assert client.post("/v1/review", json=body).status_code == 401
    r = client.post("/v1/review", json=body, headers={"X-Internal-Token": "t"})
    assert r.status_code == 200 and r.json()["decision"]["verdict"] == "retire"
