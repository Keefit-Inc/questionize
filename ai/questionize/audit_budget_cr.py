"""Reconstruct intended blind request hashes without any additional inference."""
import collections
import json
import re

from .eval_budget_cr import Answer, Procedure, TEACHER, VERIFY, Verification, question_input, solver_system
from .research_budget import digest


def request_hash(system, user, schema):
    return digest({"model":"muse-spark-1.3", "input":[{"role":"system","content":system},{"role":"user","content":user}],
        "reasoning":{"effort":"medium"}, "store":False,
        "text":{"format":{"type":"json_schema","name":schema.__name__,"strict":True,"schema":schema.model_json_schema()}}})


def audit(root):
    manifest=json.loads((root/"manifest.json").read_text());memory=json.loads((root/"memory.json").read_text());run=json.loads((root/"test.json").read_text())
    grouped=collections.defaultdict(list)
    for item in manifest["partitions"].get("train",[]):
        grouped[item["subtype"]].append({"question":item["question"],"reference_key":item["answer_key"],"expert_explanation":item["official_explanation"]})
    teacher_hashes=[request_hash(TEACHER,json.dumps({"subtype":subtype,"training_examples":items},ensure_ascii=False),Procedure) for subtype,items in sorted(grouped.items())]
    teacher_calls=memory["calls"]
    teacher_matched=sum(n<len(teacher_hashes) and c.get("request_hash")==teacher_hashes[n] for n,c in enumerate(teacher_calls))
    items={i.get("library_fingerprint"):i for i in manifest["partitions"]["test"]}
    checked=matched=pattern_hits=0
    for row in run["rows"]:
        item=items.get(row.get("fingerprint")) if row.get("fingerprint") else None
        if not item:
            checked+=sum(len(r["calls"]) for r in row["conditions"].values());continue
        question=question_input(item);user=json.dumps(question,ensure_ascii=False)
        if re.search(r'\b(?:correct|official)\s+answer\s*(?:is|:)\s*[A-E]\b|\banswer\s+key\s*:',user,re.I):pattern_hits+=1
        for arm,result in row["conditions"].items():
            expected=[request_hash(solver_system(item,memory if arm!="A" else None),user,Answer)]
            if arm=="MV" and result.get("first_result"):
                expected.append(request_hash(VERIFY+"\n"+solver_system(item,memory),
                    json.dumps({"question":question,"proposed_answer":result["first_result"]},ensure_ascii=False),Verification))
            for n,call in enumerate(result["calls"]):
                checked+=1
                matched+=n<len(expected) and call.get("request_hash")==expected[n]
    passed=teacher_matched==len(teacher_calls)==len(teacher_hashes) and checked==matched and checked>0 and pattern_hits==0
    return {"training_requests_checked":len(teacher_calls),"training_requests_matched":teacher_matched,
            "evaluation_requests_checked":checked,"evaluation_requests_matched":matched,
            "reference_pattern_hits":pattern_hits,"passed":passed}
