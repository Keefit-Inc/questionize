import json
from types import SimpleNamespace

import httpx
import pytest

from questionize.eval_budget_cr import Answer, condition, prepare, question_input
from questionize.research_budget import BudgetClient, BudgetFailure, output_limit, price


@pytest.mark.asyncio
async def test_cap_includes_hidden_reasoning_and_cache_cannot_increase_budget():
    requests = []
    def handler(request):
        body = json.loads(request.content); requests.append(body)
        assert body["store"] is False
        if request.url.path.endswith("input_tokens"):
            return httpx.Response(200,json={"input_tokens": 1200})
        assert body["max_output_tokens"] == output_limit(.03,1200)
        return httpx.Response(200,json={"status":"completed", "model":"muse-spark-1.3",
            "usage":{"input_tokens":1000,"output_tokens":2000,"input_tokens_details":{"cached_tokens":800},"output_tokens_details":{"reasoning_tokens":1800}},
            "output":[{"type":"message","content":[{"type":"output_text","text":json.dumps({"answer_label":"B","confidence":.9,"reasoning":"Abstract justification"})}]}]})
    provider=SimpleNamespace(name="meta",model="muse-spark-1.3",base_url="https://test/v1",api_key="test")
    client=BudgetClient(provider,transport=httpx.MockTransport(handler))
    try: result,metrics=await client.complete("system","question",Answer,.03)
    finally: await client.close()
    assert len(requests)==2 and result.answer_label=="B"
    assert metrics["normalised_usd"]==price(1000,2000)
    assert metrics["estimated_billed_usd"]==price(1000,2000,800)
    assert metrics["reasoning_tokens"]==1800
    assert metrics["normalised_usd"]>metrics["estimated_billed_usd"]


@pytest.mark.asyncio
async def test_missing_usage_is_not_a_zero_cost_success():
    def handler(request):
        return httpx.Response(200,json={"input_tokens":100}) if request.url.path.endswith("input_tokens") else httpx.Response(200,json={"status":"completed"})
    client=BudgetClient(SimpleNamespace(name="meta",model="muse-spark-1.3",base_url="https://test/v1",api_key="test"),transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(BudgetFailure,match="missing_usage") as raised: await client.complete("s","q",Answer,.03)
        assert raised.value.metrics["generation_calls"]==1 and not raised.value.metrics["usage_complete"]
    finally: await client.close()


def item(fingerprint,category,split,passage):
    return {"entry_id":fingerprint,"library_fingerprint":fingerprint,"library_category":category,"split":split,
        "question":{"passage":passage,"stem":"Which statement follows?","choices":[{"label":l,"text":"Choice "+l} for l in "ABCDE"]},
        "answer_key":"A","official_explanation":"PRIVATE_REFERENCE_SENTINEL","subtype":"inference"}


def test_shared_stimulus_cannot_leak_across_training_and_evaluation(tmp_path):
    passage=" ".join("word"+str(i) for i in range(45))
    records=[item("train","existing_og","train",passage),item("dev","existing_og","test",passage),
             item("alias","additional_sources","",passage),item("new","additional_sources","","Completely distinct stimulus.")]
    source=tmp_path/"library.json";source.write_text(json.dumps({"items":records}))
    out=tmp_path/"experiment";prepare(source,out)
    manifest=json.loads((out/"manifest.json").read_text())
    assert manifest["public"]["counts"]=={"train":0,"development":2,"test":1,"held":1}
    assert manifest["partitions"]["held"][0]["library_fingerprint"]=="alias"


@pytest.mark.asyncio
async def test_blind_prompts_never_receive_source_key_or_explanation():
    source=item("q","additional_sources","test","Source text")
    source["question"]["local_reference"]={"key":"A","explanation":"PRIVATE_REFERENCE_SENTINEL"}
    calls=[]
    class Scripted:
        async def complete(self,system,user,schema,allowance):
            calls.append((system,user,allowance))
            assert "PRIVATE_REFERENCE_SENTINEL" not in system+user
            assert "answer_key" not in user and "reference_key" not in user and "local_reference" not in user
            payload={"answer_label":"B","confidence":.8,"reasoning":"Public rationale"}
            if schema.__name__=="Verification":payload.update(proposed_answer_valid=True,issue="none")
            return schema(**payload),{"normalised_usd":.005}
    memory={"procedures":{"inference":{"steps":["Check entailment"]}}}
    result=await condition(Scripted(),source,"MV",memory)
    assert len(calls)==2 and calls[0][2]==.015 and calls[1][2]==.025
    assert not result["correct"] and result["answer"]=="B"
    assert set(question_input(source))=={"passage","stem","choices"}
