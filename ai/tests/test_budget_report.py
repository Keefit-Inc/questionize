import json

from questionize.budget_report import project_study
from questionize.scoreboard import render_data


def test_public_projection_drops_originals_and_unapproved_nested_strings():
    row = {"run_id": "budget-test", "protocol": "E14", "started_at": "2026-10-30T00:00:00Z", "capabilities": ["C3.1"],
           "summary": {}, "budget_study": {"schema_version": 1, "decision": "held", "candidate_deployed": True,
               "original_question": "PRIVATE_SOURCE_SENTINEL", "memory_hash": "a" * 64,
               "split": {"counts": {"train": 70, "test": 155, "source": "PRIVATE_SOURCE_SENTINEL"},
                         "membership_hashes": {"test": "b" * 64}},
               "conditions": {"A": {"n": 155, "correct": 150, "accuracy": 150/155, "explanation": "PRIVATE_SOURCE_SENTINEL",
                                     "ci95": [.9, 1], "vs_baseline": {"b": 1, "c": 0, "private": "PRIVATE_SOURCE_SENTINEL"}}},
               "slices": {"weaken": {"n": 3, "A": 2, "question": "PRIVATE_SOURCE_SENTINEL"}, "PRIVATE_SOURCE_SENTINEL": {"n": 2}},
               "diagnostics": {"harm": 1, "item": "PRIVATE_SOURCE_SENTINEL"}}}
    result = project_study(row)
    assert "PRIVATE_SOURCE_SENTINEL" not in json.dumps(result)
    assert result["candidate_deployed"] is False
    assert result["conditions"]["A"]["correct"] == 150
    assert render_data([row])["budget_studies"] == [result]
