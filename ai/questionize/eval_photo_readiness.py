"""E13: local-only real image checks using the live upload diagnosis code."""
import argparse
import asyncio
import base64
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .config import load_settings
from .errorlog import diagnose
from .eval_e1 import git_sha
from .eval_readiness import Counted, write
from .import_scan import inside_repo
from .llm import OpenAICompatLLM
from .pipeline import QuestionPipeline
from .schemas import DiagnoseRequest


async def evaluate(config, root):
    settings = load_settings()
    if settings.primary.name != "meta":
        raise ValueError("Registered evaluation uses Meta")
    raw = OpenAICompatLLM(settings.primary, timeout=75, max_retries=0)
    raw._client = raw._client.with_options(max_retries=0)
    model = Counted(raw)
    dataset = json.loads(Path(config["dataset"]).read_text())
    items = {i["entry_id"]:i for i in dataset["items"]}
    results = []
    for case in config["cases"]:
        image = Path(case["image"])
        if inside_repo(image):
            raise ValueError("Images must remain local and outside the repository")
        source = items[case["entry_id"]]
        row = {"scenario":case["scenario"], "parent":case["entry_id"], "image_sha256":hashlib.sha256(image.read_bytes()).hexdigest()}
        events = []
        async def emit(event):
            events.append(event)
        try:
            out = await diagnose(QuestionPipeline(model, model), DiagnoseRequest(level="gmat", upload_learning=True,
                images=["data:image/png;base64,"+base64.b64encode(image.read_bytes()).decode()],
                chosen_label="D", practice_count=0), emit)
            observation = out["research_observation"]
            trace = out["diagnosis"]["learning_trace"]
            captured = out["source_question"]
            def words(s):
                s = re.sub(r"\[/?BOLD_\d+\]", "", s)
                return re.findall(r"[a-z0-9]+",s.lower())
            row.update(main_correct=trace["main_answer"] == source["answer_key"], status=trace["reference_status"],
                detailed_available=trace["detailed_explanation_available"],
                evidence_contract=(out["diagnosis"]["chosen_correct"] is None and out["diagnosis"]["misconception"] is None)
                    if trace["reference_status"] in ("ai_estimated","unconfirmed","disputed") else True,
                source_roles_equal={field:words(captured[field]) == words(source["question"][field]) for field in ["passage","stem"]},
                choice_texts_equal=[words(c["text"]) for c in captured["choices"]] == [words(c["text"]) for c in source["question"]["choices"]],
                output=out, events=events)
        except Exception as e:
            row.update(error=type(e).__name__, evidence_contract=False)
        results.append(row)
        write(root/"private-results.json",results)
        print("E13",len(results),"/",len(config["cases"]),"completed; errors",sum("error" in r for r in results),flush=True)
    await raw._client.close()
    return {"expected":len(results),"completed":sum("error" not in r for r in results),"errors":sum("error" in r for r in results),
        "parents":len({r["parent"] for r in results}),"calls":model.calls,"correct":sum(r.get("main_correct",False) for r in results),
        "evidence_contract_passed":sum(r["evidence_contract"] for r in results),
        "source_text_roles_equal":sum(all(r.get("source_roles_equal",{}).values()) and r.get("choice_texts_equal",False) for r in results),
        "detailed_available":sum(r.get("detailed_available",False) for r in results),
        "statuses":{s:sum(r.get("status")==s for r in results) for s in ["ai_estimated","unconfirmed","disputed","supplied_reference"]}}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config",type=Path)
    parser.add_argument("--version",type=int,choices=[1,2],default=1)
    args=parser.parse_args()
    if inside_repo(args.config):raise SystemExit("Private local configuration required")
    config=json.loads(args.config.read_text())
    root=Path.home()/"questionize-research"/"runs"/(datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-e13-photos")
    root.mkdir(mode=0o700)
    manifest={"run_id":root.name,"protocol":"E13","protocol_version":args.version,"subject":"CR","evaluation_scope":"development",
        "started_at":datetime.now(timezone.utc).isoformat(),"git_sha":git_sha(),"config_hash":hashlib.sha256(args.config.read_bytes()).hexdigest()}
    write(root/"manifest.json",manifest)
    for name in ["eval_photo_readiness.py","upload_learning.py","errorlog.py","integrity.py","prompts.py"]:
        (root/name).write_bytes(Path(__file__).with_name(name).read_bytes());(root/name).chmod(0o600)
    print("PRIVATE RUN",root,flush=True)
    summary=asyncio.run(evaluate(config,root));write(root/"summary.json",summary)
    entry={**manifest,"capabilities":[],"n_items":3,"summary":{"evidence_contract":summary},
        "note":"Three deliberately selected photo scenarios from two known hard parents. Engineering evidence, no population capture/explanation/learner metric."}
    with (Path(__file__).resolve().parents[2]/"research/ledger.jsonl").open("a") as f:f.write(json.dumps(entry)+"\n")
    print(json.dumps(summary,indent=2),flush=True)


if __name__ == "__main__":
    main()
