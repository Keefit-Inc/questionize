import pytest
from questionize.research_map import project_registry


def test_projection_connects_a_paper_to_real_runs_without_exporting_private_fields():
    registry = {"schema_version": 1, "papers": [{"id": "p", "title": "Study", "url": "https://arxiv.org/abs/2308.10144",
        "capabilities": ["C3.1"], "claim": "Claim", "limitations": "Limited", "implementation_status": "adapted",
        "review_status": "abstract_checked", "protocols": ["E1"], "implementation_paths": ["ai/questionize/memory.py", "/private/raw.json"],
        "private_explanation": "SECRET"}], "evaluations": [{"run_id": "run", "summary": {"calls": 2, "question": "SECRET"}}]}
    out = project_registry(registry, [{"run_id": "run", "protocol": "E1"}])
    assert out["papers"][0]["runs"][0]["run_id"] == "run"
    assert out["papers"][0]["implementation_paths"] == ["ai/questionize/memory.py"]
    assert "SECRET" not in str(out)
    registry["papers"][0]["url"] = "javascript:alert(1)"
    with pytest.raises(ValueError):
        project_registry(registry, [])
