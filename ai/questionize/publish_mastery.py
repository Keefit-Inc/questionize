"""Publish E15 summaries only; original questions/keys/outputs are never copied."""
import argparse
import json
from pathlib import Path

from .mastery_report import build,project

RESEARCH=Path(__file__).resolve().parents[2]/'research'
NAMES={'SM':'Spark medium direct','S':'Spark high direct','P':'Spark high + mechanisms','W':'Wonder high direct','PW':'Wonder high + mechanisms'}


def report(entry):
    s=entry['mastery_study'];selected=s['candidate'];official=s['phases']['regression']['roles']['official_regression'][selected]
    confirmation=s['phases']['confirm'];counts=s['split']['counts']
    lines=[f"# E15 v{entry['protocol_version']} — GMAT CR Solver mastery study",'',
        '## Outcome','',
        f"Selected configuration: **{NAMES[selected]}**. Decision: **{s['decision']}**. Research candidate deployed: **no**.",
        f"Official, previously exposed regression: **{official['correct']}/{official['n']}** against source keys. Untouched compilation confirmation: **{confirmation['conditions'][selected]['correct']}/{confirmation['conditions'][selected]['n']}** evaluated, out of {confirmation['registered']} registered.",
        'A perfect fixed cohort is a development/confirmation observation, not proof of universal 100% reliability. This study does not train model weights. Model upgrades and inference effort are separate from any procedure/tool effect.','',
        f"Run `{entry['run_id']}`; final configuration source commit `{entry['git_sha']}`.",'',
        '## Private sources and roles','',
        '| Role | Questions | Stimulus groups | Membership SHA-256 |','|---|---:|---:|---|']
    for role,n in counts.items():lines.append(f"| {role} | {n} | {s['split']['groups'][role]} | `{s['split']['hashes'][role]}` |")
    lines += ['',f"Unique questions evaluated: **{s['unique_evaluated']}**. Condition responses: {s['condition_responses']}. Repeated diagnostic trials are counted once in unique-question coverage. Held records were identified before inference; LSAT records are unused.",
        'Official OG records were previously exposed and used for source-assisted failure diagnosis. E14 sources are also exposed regressions. The new compilation has supplied keys only, no expert explanations and no independent human adjudication. Its original source/exam labels and possible pretraining exposure limit generalisation. No unresolved key mapping is silently treated as truth.','',
        '## Final confirmation','',
        '| Condition | Source matches / evaluated | Accuracy | Wilson 95% interval | Normalised cost | Estimated billed | Errors |',
        '|---|---:|---:|---|---:|---:|---:|']
    if s.get('preparation',{}).get('restored_questions'):
        prep=s['preparation'];lines[lines.index('## Final confirmation'):lines.index('## Final confirmation')]=[
            '## Source preparation incident and correction','',
            f"An earlier compilation development phase was stopped after missing shared passages were found. It recorded {prep['invalid_evaluated_questions']} observations; none is used as Solver-quality evidence. The original phase and its cost remain preserved. Deterministic source-index restoration repaired {prep['restored_questions']} GMAT records, with {prep['keys_changed']} key changes and {prep['choices_changed']} choice changes. Confirmation had not started. Source-test role assignment was preserved.",
            f"Discarded-phase known cost: ${prep['invalid_phase_normalised_usd']:.6f} normalised / ${prep['invalid_phase_estimated_billed_usd']:.6f} estimated billed. Interrupted request reservations add a conservative upper-bound charge of ${prep['aborted_reservation_upperbound_usd']:.6f}. Unknown billing remains explicit. Valid official controls were reused only after identical request-hash certification, not silently re-executed or called fresh.",'',
            f"Blinding audit passed: {s['blinding_passed']}; {s['matched_requests']}/{s['audited_requests']} request hashes reconstructed from the permitted question/strategy/tool fields. Full source originality or absence from model pretraining is not established by this audit.",'']
    for name,row in confirmation['conditions'].items():
        ci=row.get('ci95');interval=f"{ci[0]*100:.2f}%–{ci[1]*100:.2f}%" if ci else 'not available'
        accuracy=f"{row['accuracy']*100:.2f}%" if row.get('accuracy') is not None else 'not evaluated'
        lines.append(f"| {NAMES[name]} | {row['correct']}/{row['n']} | {accuracy} | {interval} | ${row['normalised_usd']:.6f} | ${row['estimated_billed_usd']:.6f} | {row['errors']} |")
    lines += ['',f"Completeness: {confirmation['evaluated']}/{confirmation['registered']}; budget-limited: {confirmation['budget_limited']}. No unattempted record is called solved. Errors remain in evaluated denominators. Model/effort configurations, policy hash and source-test memberships were frozen before this phase.",
        'Each final arm has its recorded common per-item ceiling; actual token usage differs. A higher model score is not credited to memory when the model itself changed.','',
        '| Paired contrast | Gained | Lost | Difference | Group-bootstrap 95% difference interval | McNemar p |',
        '|---|---:|---:|---:|---|---:|']
    for name,row in confirmation['conditions'].items():
        c=row.get('comparison')
        if not c:continue
        interval=c.get('diff_ci95',[])
        lines.append(f"| {name} vs {row['baseline']} | {c['b']} | {c['c']} | {c['difference']*100:+.2f} pp | {interval[0]*100:+.2f} to {interval[1]*100:+.2f} pp | {c['p']} |")
    lines += ['', 'These are descriptive comparisons of a fixed source sample. Small samples, repeated model errors and source-key uncertainty do not support universal superiority or 99.9% claims. An empirical zero-width difference interval does not prove a population effect is zero.','',
        '## Development and regression phases','']
    for name,phase in s['phases'].items():
        lines += [f"### {name}",'',f"Evaluated {phase['evaluated']}/{phase['registered']} observations, {phase['unique_questions']} distinct questions; budget-limited {phase['budget_limited']}.",
            '', '| Condition | Matches | Errors | Failed optional repairs | Known hard trials matched | Known hard cases closed | Estimated billed |',
            '|---|---:|---:|---:|---:|---:|---:|']
        for arm,row in phase['conditions'].items():lines.append(f"| {NAMES[arm]} | {row['correct']}/{row['n']} | {row['errors']} | {row['repair_errors']} | {row['hard_correct']}/{row['hard_trials']} | {row['hard_closed']}/{row['hard_unique']} | ${row['estimated_billed_usd']:.6f} |")
        if name=='pilot':lines += ['', 'Two known hard cases were each repeated twice, plus six controls: ten responses are eight distinct questions, not ten independent samples.']
        if name=='regression':
            for role,values in phase['roles'].items():
                for arm,row in values.items():lines += ['',f"{role}, {NAMES[arm]}: **{row['correct']}/{row['n']}**. This is an exposed regression result, not untouched evaluation."]
    lines += ['', '## Methods, costs and limitations','',
        'The mechanism condition replaces keyword routing with a task/option audit and private, source-derived procedures. It explicitly distinguishes given facts from invented links, strengthening from deductive sufficiency, and argument-level claims from internal causal wording. A bounded exact-arithmetic checker can generate a rate/count counterexample conditional on the model-proposed semantic mapping. It executes no model-authored code. This arithmetic does not certify the complete natural-language question.',
        'Only checked numeric witnesses may trigger the optional tool-informed repair. A failed optional repair preserves a completed initial answer. All attempted and failed calls are metered; a model consensus is not used as a new answer label.',
        f"Normalised token-price spending ${s['normalised_usd']:.6f}; estimated billed token cost ${s['estimated_billed_usd']:.6f}; conservative global charge ${s['charged_usd']:.6f} under a ${s['budget_limit_usd']:.2f} envelope. Complete response usage: {s['cost_accounting_complete']}. Account invoices and unrelated production traffic are not measured.",
        'Meta Standard models, Responses API, explicit effort, store=false, no generation retries. Token prices reviewed 2026-10-30: Spark input/cache/output $1.25/$0.15/$4.25 per million; Wonder $4/$0.20/$20. Hidden reasoning is included in output usage. [Meta pricing](https://dev.meta.ai/docs/pricing-rate-limits).',
        'The final test is consumed once for this frozen selection. Future use of these errors is development, requiring a new confirmation set. Expert originals, AI-derived methods, key-only references and learner activity remain distinct. No material was imported into a learner account or Bank. Explanation quality, defect detection and educational outcomes remain separately unmeasured.','',
        f"Manifest `{s['manifest_hash']}`; private procedure `{s['policy_hash']}`; configuration source `{s['source_hash']}`.",'',
        f"[Protocol](../protocols/{Path(s['protocol_path']).name}) · [pre-confirmation clarification](../protocols/E15-solver-mastery-clarification.md) · [runner](../../ai/questionize/eval_mastery.py) · [console](https://questionize.org/admin#mastery)",'']
    return '\n'.join(lines)


def publish(root,research=RESEARCH):
    entry=build(root);study=project(entry);entry['mastery_study']=study
    # Ledger summary is already scalar aggregates; keep field-level projection for all richer data.
    path=research/'ledger.jsonl';old=[json.loads(x) for x in path.read_text().splitlines() if x] if path.exists() else []
    found=[r for r in old if r.get('run_id')==entry['run_id']]
    if found and found!=[entry]:raise ValueError('Append a correction instead of changing a recorded run')
    if not found:
        with path.open('a') as handle:handle.write(json.dumps(entry,ensure_ascii=False,allow_nan=False)+'\n')
    (research/'results').mkdir(exist_ok=True);(research/'results/E15.md').write_text(report(entry))
    print(json.dumps({'run_id':entry['run_id'],'decision':study['decision'],'unique_questions':study['unique_evaluated'],
        'confirmation':{a:{k:v[k] for k in ('n','correct','errors')} for a,v in study['phases']['confirm']['conditions'].items()},
        'official_regression':study['phases']['regression']['roles']['official_regression'],'estimated_billed_usd':study['estimated_billed_usd']}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--experiment',type=Path,required=True);args=p.parse_args();publish(args.experiment)
