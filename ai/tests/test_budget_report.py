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


def test_publishing_preserves_null_results_errors_and_private_boundaries(tmp_path):
    from questionize.eval_budget_cr import private_write
    from questionize.publish_budget_cr import publish
    from questionize.research_budget import digest
    root = tmp_path / "private"; research = tmp_path / "public"; research.mkdir()
    public = {"counts": {"train": 1, "development": 0, "test": 5, "held": 0},
              "groups": {"train": 1, "development": 0, "test": 5, "held": 0},
              "membership_hashes": {name: digest(name) for name in ("train","development","test","held")},
              "overlap_links": 0, "cross_partition_group_overlap": 0}
    manifest = {"public": public, "partitions": {"test": [{"question": {"stem":"Which conclusion follows logically?"}} for _ in range(5)]}}
    metric = {"generation_calls": 1, "normalised_usd": .001, "estimated_billed_usd": .001,
              "input_tokens": 100, "output_tokens": 200, "reasoning_tokens": 100, "cached_tokens": 0,
              "elapsed_seconds": 1., "usage_complete": True, "max_output_tokens": 200}
    memory = {"hash": "d"*64, "procedures": {"inference": {}}, "calls": [metric], "failures": []}
    rows=[]
    # both right, rescue, harm, both wrong, operational failure
    for n,(a,m,first,final,error) in enumerate([(True,True,True,True,None),(False,True,False,True,None),
        (True,True,True,False,None),(False,False,False,False,None),(True,False,False,False,"incomplete_response")]):
        conditions={}
        for arm,correct in [("A",a),("M",m),("MV",final)]:
            conditions[arm]={"correct":correct,"first_correct":first if arm=="MV" else correct,
                             "first_answer":"B","answer": "B" if correct else "C", "calls":[metric],
                             "error":error if arm=="MV" else None,"reasoning":"PRIVATE_SOURCE_SENTINEL"}
        rows.append({"stimulus_group":str(n),"type":"inference","conditions":conditions})
    run={"rows":rows,"expected":5,"finished_at":"done","started_at":"2026-10-30T12:00:00.000000+00:00",
         "memory_hash":memory["hash"],"manifest_hash":digest(manifest),"runner_hash":"a"*64,"client_hash":"b"*64,"git_sha":"revision"}
    for name,obj in [("manifest",manifest),("memory",memory),("test",run),("smoke",{"rows":[]})]:private_write(root/(name+".json"),obj)
    publish(root,research)
    before=(research/"ledger.jsonl").read_text();publish(root,research)
    assert (research/"ledger.jsonl").read_text()==before
    assert "PRIVATE_SOURCE_SENTINEL" not in before+(research/"results/E14.md").read_text()
    entry=json.loads(before)
    assert entry["summary"]["MV"]["n"]==5 and entry["summary"]["MV"]["errors"]==1
    assert entry["budget_study"]["decision"]=="held"
    assert entry["budget_study"]["diagnostics"]["rescue"]==1
    assert entry["budget_study"]["diagnostics"]["harm"]==1
    assert entry["budget_study"]["operational_errors"]["MV"]["output_budget_exhausted"]==1
