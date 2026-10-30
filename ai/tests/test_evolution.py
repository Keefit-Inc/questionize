from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from conftest import ARTICLE, FakeJudgeLLM, ScriptedLLM, flat_scores, make_analysis, make_question, passing_critic, solver
from questionize.app import create_app
from questionize.build_evolution_benchmark import build
from questionize.config import ProviderConfig, Settings
from questionize.evolution import Benchmark, EvaluationRequest, ProbeRequest, Proposal, ProposalRequest, case_decision, content_hash, evaluate, probe
from questionize.judge import ArgumentJudge
from questionize.operator_policy import policy_trace, task_operator
from questionize.pipeline import QuestionPipeline
from questionize.reviewer import review
from questionize.schemas import CapabilityPolicy, GenerateRequest, ReviewDecision, ReviewRequest


def policy(mode="legacy", name="policy"):
    payload = {"except_mode": mode}
    return {"id": name, "hash": content_hash(payload), "payload": payload}


def cases():
    standard = [{"case_id": f"standard_{i:03d}", "subtype": "strengthen", "operator": "standard", "solver_answer": "A",
                 "judge_answer": "B", "judge_first_rate": 1.0, "key": "B", "baseline_answer": "B"} for i in range(34)]
    return standard + [{"case_id": "except_case", "subtype": "strengthen", "operator": "except", "solver_answer": "E",
                        "judge_answer": "C", "judge_first_rate": 1.0, "key": "E", "baseline_answer": "C"}]


def request(before="legacy", after="abstain"):
    recorded = cases()
    return {"baseline": policy(before, "before"), "candidate": policy(after, "after"),
            "benchmark": {"id": "fixed-replay", "kind": "decision_replay", "hash": content_hash(recorded), "cases": recorded}}


def client(model=None):
    cfg = ProviderConfig("meta", "http://example.invalid", "scripted", "scripted-meta")
    return TestClient(create_app(Settings(primary=cfg, solver=cfg, internal_token="internal"),
                                 QuestionPipeline(model or ScriptedLLM(), ScriptedLLM())))


def test_replay_fixes_one_wrong_override_without_changing_standard_decisions():
    result = evaluate(EvaluationRequest.model_validate(request()))
    assert result["baseline"]["correct"] == 34 and result["candidate"]["correct"] == 35
    assert result["baseline"]["n"] == result["candidate"]["n"] == 35
    assert result["comparison"]["gained"] == 1 and result["comparison"]["lost"] == 0
    assert result["comparison"]["standard_changes"] == 0
    assert result["gate"]["passed"] is True
    assert result["evidence_scope"] == "development_regression"
    assert result["baseline"]["calls"] == 0  # no fresh model inference is claimed


def test_already_active_candidate_is_held_and_historical_integrity_still_uses_legacy():
    result = evaluate(EvaluationRequest.model_validate(request("abstain", "abstain")))
    assert result["baseline"]["correct"] == result["candidate"]["correct"] == 35
    assert result["gate"]["passed"] is False
    assert "unchanged_policy" in result["gate"]["reasons"]
    assert "no_measured_improvement" in result["gate"]["reasons"]


def test_regressing_policy_is_held():
    result = evaluate(EvaluationRequest.model_validate(request("abstain", "legacy")))
    assert result["gate"]["passed"] is False
    assert "regression_detected" in result["gate"]["reasons"]


def test_incomplete_and_tampered_evidence_is_not_adopted():
    payload = request()
    payload["benchmark"]["cases"] = payload["benchmark"]["cases"][-2:]
    payload["benchmark"]["hash"] = content_hash(payload["benchmark"]["cases"])
    assert "insufficient_regression_cases" in evaluate(EvaluationRequest.model_validate(payload))["gate"]["reasons"]
    payload["benchmark"]["cases"][0]["key"] = "C"
    with pytest.raises(ValidationError, match="benchmark hash"):
        EvaluationRequest.model_validate(payload)
    payload["benchmark"]["hash"] = content_hash(payload["benchmark"]["cases"])
    payload["benchmark"]["cases"][0]["baseline_answer"] = "A"
    payload["benchmark"]["hash"] = content_hash(payload["benchmark"]["cases"])
    with pytest.raises(ValueError, match="legacy decisions"):
        evaluate(EvaluationRequest.model_validate(payload))


def test_private_text_is_rejected_and_policy_hash_cannot_be_forged():
    payload = request()
    payload["benchmark"]["cases"][0]["passage"] = "private wording must not enter this interface"
    with pytest.raises(ValidationError, match="Extra inputs"):
        EvaluationRequest.model_validate(payload)
    with pytest.raises(ValidationError, match="policy hash"):
        CapabilityPolicy.model_validate({**policy(), "hash": "0" * 64})
    with pytest.raises(ValidationError, match="numeric aggregates"):
        ProposalRequest(baseline={"except_mode": "legacy"}, observations={"source_text": "private passage"})


def test_probe_and_live_policy_share_the_same_guard_and_scope():
    p = CapabilityPolicy.model_validate(policy("abstain"))
    example = EvaluationRequest.model_validate(request()).benchmark.cases[-1]
    result = probe(ProbeRequest(policy=p, case=example))
    assert result["chosen_answer"] == "E" and result["judge_abstained"]
    assert result["policy_hash"] == p.hash
    assert result["runtime"] == "shared_operator_policy"
    assert policy_trace(p, subject="CR", level="lsat", subtype="strengthen", operator="except")["judge_abstained"] is False
    assert task_operator("All these support the plan EXCEPT:") == "except"
    assert task_operator("Which most supports the plan?") == "standard"


@pytest.mark.parametrize("path,body", [("propose", {"baseline": {"except_mode": "legacy"}}), ("evaluate", request()), ("probe", {"policy": policy(), "case": cases()[0]})])
def test_research_routes_require_internal_token(path, body):
    assert client().post("/v1/research/" + path, json=body).status_code == 401


def test_proposal_uses_one_scripted_model_call_and_replay_needs_no_model():
    model = ScriptedLLM(Proposal=[Proposal(except_mode="abstain", reason="Subtype ranking reverses the requested task.", hypothesis="Abstaining fixes the recorded EXCEPT override without changing standard cases.")])
    app = client(model)
    response = app.post("/v1/research/propose", json={"baseline": {"except_mode": "legacy"}, "observations": {"except_wrong_overrides": 1}}, headers={"X-Internal-Token": "internal"})
    assert response.status_code == 200
    assert response.json()["payload"] == {"except_mode": "abstain"}
    assert response.json()["logical_calls"] == 1 and len(model.calls) == 1
    result = app.post("/v1/research/evaluate", json=request(), headers={"X-Internal-Token": "internal"})
    assert result.status_code == 200 and result.json()["gate"]["passed"]
    assert len(model.calls) == 1


async def test_real_generation_verifier_applies_request_policy_without_mutating_shared_pipeline():
    except_question = make_question("B").model_copy(update={"subtype": "strengthen", "stem": "Every statement strengthens the argument EXCEPT:"})
    judge_model = FakeJudgeLLM(flat_scores(B=(0.9, 0.2)))
    primary = ScriptedLLM(ArticleAnalysis=[make_analysis()], Question=[except_question], CriticResult=[passing_critic()])
    pipeline = QuestionPipeline(primary, ScriptedLLM(SolverResult=[solver("B")]), judge=ArgumentJudge([judge_model], seed=7))
    events = []

    async def emit(event):
        events.append(event)

    req = GenerateRequest(text=ARTICLE, types=["CR"], capability_policy=policy("abstain"))
    result = await pipeline.run(req, emit)
    assert result.questions[0].verification.verified
    assert result.questions[0].verification.capability_policy["judge_abstained"]
    assert result.questions[0].verification.capability_policy["judge_gate_reached"]
    assert result.questions[0].verification.capability_policy["judge_called"] is False
    assert judge_model.calls == 0
    assert any(e.get("capability_policy", {}).get("policy_id") == "policy" for e in events)
    # Same pipeline, other level: the policy is out of scope and the Judge still runs.
    result = await pipeline.run(req.model_copy(update={"level": "lsat"}))
    assert judge_model.calls == 3
    assert result.questions[0].verification.capability_policy["applied"] is False


async def test_policy_fixes_inapplicable_judge_gate_but_keeps_solver_and_critic_required():
    question = make_question("B").model_copy(update={"subtype": "strengthen", "stem": "Each of the following supports the conclusion EXCEPT:"})
    judge_model = FakeJudgeLLM(flat_scores(B=(-0.4, 0.2), C=(0.9, 0.2)))
    primary = ScriptedLLM(ArticleAnalysis=[make_analysis()], Question=[question], CriticResult=[passing_critic()])
    pipeline = QuestionPipeline(primary, ScriptedLLM(SolverResult=[solver("B")]), max_revisions=0, judge=ArgumentJudge([judge_model], seed=7))
    legacy = await pipeline.run(GenerateRequest(text=ARTICLE, types=["CR"], capability_policy=policy("legacy")))
    assert not legacy.questions[0].verification.verified
    assert legacy.questions[0].judge.verdict == "wrong_key"
    old_calls = judge_model.calls
    candidate = await pipeline.run(GenerateRequest(text=ARTICLE, types=["CR"], capability_policy=policy("abstain")))
    assert candidate.questions[0].verification.verified
    assert candidate.questions[0].verification.critic_verdict == "pass"
    assert candidate.questions[0].verification.solver_answer == "B"
    assert judge_model.calls == old_calls
    assert candidate.questions[0].judge is None
    assert candidate.questions[0].verification.capability_policy["judge_abstained"]


async def test_review_uses_pinned_policy_for_initial_judgment_and_revision():
    question = make_question("B").model_copy(update={"subtype": "strengthen", "stem": "All these support the argument EXCEPT:"})
    judge_model = FakeJudgeLLM(flat_scores(B=(-.4, .2), C=(.9, .2)))
    primary = ScriptedLLM(ReviewDecision=[ReviewDecision(verdict="revise", findings=["Clarify the explanation."], revision_guidance="Keep the verified task operator.")],
                          Question=[question], CriticResult=[passing_critic()])
    pipeline = QuestionPipeline(primary, ScriptedLLM(SolverResult=[solver("B")]), judge=ArgumentJudge([judge_model], seed=7))
    result = await review(pipeline, ReviewRequest(question=question, capability_policy=policy("abstain")))
    assert result.revised.verification.verified
    assert result.capability_policy["judge_abstained"]
    assert result.revised.verification.capability_policy["judge_abstained"]
    assert result.capability_policy["policy_hash"] == result.revised.verification.capability_policy["policy_hash"]
    assert judge_model.calls == 0


def test_benchmark_builder_keeps_only_abstract_verified_test_inputs():
    question = {"passage": "PRIVATE SOURCE WORDING", "stem": "Each supports the conclusion EXCEPT:", "choices": []}
    item = {"entry_id": 99, "answer_key": "E", "key_verdict": "book", "split": "test", "flagged": False, "subtype": "strengthen", "question": question}
    outcomes = [{"entry_id": 99, "condition": "B1", "key": "E", "answer": "C", "notes": {"solver": "E", "judge_top": "C", "judge_first_rate": 1.0}}]
    data = {"dataset": "private", "items": [item, {**item, "entry_id": 100, "subtype": "structure"}, {**item, "entry_id": 101, "flagged": True}, {**item, "entry_id": 102, "split": "train"}]}
    output = build(data, outcomes, "parent-hash", "baseline-run")
    assert output["n_cases"] == 1 and output["observations"]["except_wrong_overrides"] == 1
    assert "PRIVATE SOURCE WORDING" not in str(output)
    assert "entry_id" not in str(output) and output["cases"][0]["case_id"] != "99"
    assert output["excluded"] == {"flagged": 1, "structure": 1, "not_test": 1, "missing_baseline": 0, "unverified_key": 0}
