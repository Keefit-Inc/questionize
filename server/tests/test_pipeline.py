from __future__ import annotations

import json

from fastapi.testclient import TestClient

from conftest import ARTICLE, ScriptedLLM, make_analysis, make_question, passing_critic, solver
from questionize.app import create_app
from questionize.config import ProviderConfig, Settings
from questionize.pipeline import QuestionPipeline
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


def test_stream_endpoint_emits_ndjson_and_done():
    primary = ScriptedLLM(
        ArticleAnalysis=[make_analysis()], Question=[make_question("B")], CriticResult=[passing_critic()]
    )
    blind = ScriptedLLM(SolverResult=[solver("B")])
    p = ProviderConfig("meta", "http://x", "k", "m")
    app = create_app(Settings(primary=p, solver=p), QuestionPipeline(primary, blind))
    client = TestClient(app)

    r = client.post("/api/questions/stream", json={"text": ARTICLE, "types": ["CR"]})
    assert r.status_code == 200
    events = [json.loads(line) for line in r.text.splitlines() if line]
    assert events[-1]["stage"] == "done"
    assert events[-1]["result"]["questions"][0]["verification"]["verified"] is True

    assert client.get("/health").json()["ok"] is True


def test_rejects_too_short_text():
    p = ProviderConfig("meta", "http://x", "k", "m")
    client = TestClient(create_app(Settings(primary=p, solver=p), QuestionPipeline(ScriptedLLM(), ScriptedLLM())))
    assert client.post("/api/questions", json={"text": "too short"}).status_code == 422
