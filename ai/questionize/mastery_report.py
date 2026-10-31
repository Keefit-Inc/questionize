"""E15 aggregate evidence and explicit public projection; originals remain private."""
import collections
import json
import math
from pathlib import Path

from .budget_report import fields,hashes,numeric
from .eval_budget_cr import compare
from .eval_e1 import wilson
from .research_budget import digest
from .mastery_audit import audit_phase

ROLES=('official_regression','web_regression','compendium_development','confirmation','held')
PHASES=('pilot','effort','ogdev','docdev','confirm','regression')
ARMS=('SM','S','P','W','PW')
METRICS=('n','expected_n','correct','accuracy','errors','repair_errors','calls','normalised_usd','estimated_billed_usd',
         'input_tokens','output_tokens','reasoning_tokens','cached_tokens','mean_seconds','tool_witnesses','repair_rescues','repair_harms',
         'hard_trials','hard_correct','hard_unique','hard_closed')


def metrics(rows,arm,expected,targets=()):
    values=[r['conditions'][arm] for r in rows];calls=[c for v in values for c in v['calls']];n=len(rows);correct=sum(v['correct'] for v in values)
    hard=[r for r in rows if r.get('entry_id') in targets]
    bycase=collections.defaultdict(list)
    for r in hard:bycase[r['fingerprint']].append(r['conditions'][arm]['correct'])
    return {'n':n,'expected_n':expected,'correct':correct,'accuracy':correct/n if n else None,
        'ci95':list(wilson(correct,n)) if n else None,'errors':sum(bool(v['error']) for v in values),
        'repair_errors':sum(bool(v.get('repair_error')) for v in values),'calls':sum(c['generation_calls'] for c in calls),
        **{name:round(sum(c.get(name,0) for c in calls),9) for name in
           ('normalised_usd','estimated_billed_usd','input_tokens','output_tokens','reasoning_tokens','cached_tokens')},
        'mean_seconds':round(sum(c['elapsed_seconds'] for c in calls)/n,3) if n else 0,
        'usage_complete':all(c['usage_complete'] or not c['generation_calls'] for c in calls),
        'tool_witnesses':sum((v.get('tool') or {}).get('status')=='counterexample_checked' for v in values),
        'repair_rescues':sum(not v['first_correct'] and v['correct'] for v in values),
        'repair_harms':sum(v['first_correct'] and not v['correct'] for v in values),
        'hard_trials':len(hard),'hard_correct':sum(r['conditions'][arm]['correct'] for r in hard),
        'hard_unique':len(bycase),'hard_closed':sum(all(v) for v in bycase.values())}


def phase_summary(run,targets):
    rows=run['rows'];result={'registered':run['expected'],'evaluated':len(rows),
        'unique_questions':len({r['fingerprint'] for r in rows}),'budget_limited':run['budget_limited'],
        'completed':bool(run.get('finished_at')),'conditions':{},'roles':{}}
    for arm,config in run['arms'].items():
        row=metrics(rows,arm,run['expected'],targets)
        if run['phase']=='pilot':row['ci95']=None # Repeated development observations are not independent cases.
        baseline='W' if arm=='PW' and 'W' in run['arms'] else 'S'
        if arm!=baseline and baseline in run['arms'] and rows:
            remapped=[{'stimulus_group':r['stimulus_group'],'conditions':{'A':r['conditions'][baseline],arm:r['conditions'][arm]}} for r in rows]
            row['comparison']=compare(remapped,arm);row['baseline']=baseline
        result['conditions'][arm]={**row,**config}
    if run['phase']=='regression':
        for role in ('official_regression','web_regression'):
            selected=[r for r in rows if r['role']==role]
            result['roles'][role]={a:metrics(selected,a,124 if role=='official_regression' else 155,targets) for a in run['arms']}
    return result


def build(root):
    manifest=json.loads((root/'manifest.json').read_text());selection=json.loads((root/'selected.json').read_text())
    reuse_path=root/'reuse-certificate.json';reuse=json.loads(reuse_path.read_text()) if reuse_path.exists() else {}
    phases={};raws={};covered=set();responses=0
    for name in PHASES:
        path=root/(name+'.json')
        if not path.exists():continue
        run=json.loads(path.read_text())
        if not run.get('finished_at'):raise ValueError('Do not publish an unfinished phase')
        if run['manifest_hash']!=digest(manifest):
            if reuse.get(name,{}).get('original_run_hash')!=digest(run):raise ValueError('Uncertified cross-manifest phase reuse')
        phases[name]=phase_summary(run,selection['policy']['diagnostic_targets']);raws[name]=run
        covered.update(r['fingerprint'] for r in run['rows']);responses+=sum(len(r['conditions']) for r in run['rows'])
    if not {'confirm','regression'}<=set(phases):raise ValueError('Final confirmation and regression phases required')
    confirmation=phases['confirm'];candidate=selection['candidate'];baseline=selection['baseline']
    official=phases['regression']['roles']['official_regression'][candidate]
    selected=confirmation['conditions'][candidate]
    gain=selected.get('comparison',{}).get('difference',0)>0
    no_errors=selected['errors']==0 and selected['repair_errors']==0
    all_costs=all(v['usage_complete'] for p in phases.values() for v in p['conditions'].values())
    official_closed=official['n']==124 and official['correct']==124 and official['errors']==0
    budget=json.loads((root/'budget-state.json').read_text())
    items={i['library_fingerprint']:i for values in manifest['partitions'].values() for i in values}
    audits={name:audit_phase(run,items,selection['policy']) for name,run in raws.items()}
    blinded=all(a['passed'] for a in audits.values())
    selected_costs=selected['usage_complete'] and phases['regression']['conditions'][candidate]['usage_complete']
    decision='confirmation_candidate' if official_closed and confirmation['evaluated']==confirmation['registered'] and gain and no_errors and selected_costs and blinded else 'held'
    incident_path=root/'preparation-incident.json';incident=json.loads(incident_path.read_text()) if incident_path.exists() else {}
    discarded_normalised=incident.get('invalid_phase_normalised_usd',0.)
    discarded_billed=incident.get('invalid_phase_estimated_billed_usd',0.)
    version=manifest.get('protocol_version',1)
    protocol='research/protocols/E15-solver-mastery-v2.md' if version==2 else 'research/protocols/E15-solver-mastery.md'
    study={'schema_version':1,'split':manifest['public'],'candidate':candidate,'baseline':baseline,
        'interpretation':selection['interpretation'],'phases':phases,'decision':decision,'candidate_deployed':False,
        'official_closed':official_closed,'unique_evaluated':len(covered),'condition_responses':responses,
        'budget_limit_usd':budget['limit_usd'],'charged_usd':budget['charged_usd'],'unknown_usage':budget['unknown_usage'],
        'normalised_usd':sum(v['normalised_usd'] for p in phases.values() for v in p['conditions'].values())+discarded_normalised,
        'estimated_billed_usd':sum(v['estimated_billed_usd'] for p in phases.values() for v in p['conditions'].values())+discarded_billed,
        'cost_accounting_complete':all_costs and budget['unknown_usage']==0,'confirmation_cost_accounting_complete':selected_costs,
        'blinding_passed':blinded,'audited_requests':sum(a['requests_checked'] for a in audits.values()),
        'matched_requests':sum(a['requests_matched'] for a in audits.values()),'preparation':incident,
        'manifest_hash':digest(manifest),'policy_hash':selection['policy_hash'],
        'source_hash':selection['source_hash'],'report_path':'research/results/E15.md','protocol_path':protocol,
        'clarification_path':'research/protocols/E15-solver-mastery-clarification.md','protocol_version':version}
    run=raws['confirm'];summary={a:{k:v for k,v in row.items() if k in (*METRICS,'ci95','usage_complete')}
        for a,row in confirmation['conditions'].items()}
    entry={'run_id':run['started_at'].replace('-','').replace(':','').split('.')[0]+'Z-e15-'+digest(manifest)[:6],
        'protocol':'E15','protocol_version':version,'subject':'CR','started_at':run['started_at'],'git_sha':run['git_sha'],
        'evaluation_scope':'full' if confirmation['evaluated']==confirmation['registered'] else 'trial',
        'capabilities':['C3.1'],'dataset_id':'private-gmat-compendium-confirmation-e15-v'+str(version),
        'dataset_hash':manifest['public']['hashes']['confirmation'],'split':'frozen_source_test_groups',
        'prompts_hash':selection['source_hash'],'models':{a:c['model'] for a,c in selection['arms'].items()},
        'n_items':run['expected'],'summary':summary,'mastery_study':study,
        'note':'Source-key agreement, with official exposed regressions and supplied-key-only confirmation kept separate. Model/effort effects are distinct from procedural learning; no universal 100% or weight-training claim.'}
    return entry


def project_metric(value):
    result=fields(value,METRICS)
    result['usage_complete']=value.get('usage_complete') is True
    for name in ('ci95',):
        v=value.get(name)
        if isinstance(v,list) and len(v)==2 and all(numeric(n) for n in v):result[name]=v
    for name,allowed in (('model',('muse-spark-1.3','muse-wonder-1.0')),('effort',('medium','high','max')),('method',('direct','mechanism')),('baseline',ARMS)):
        if value.get(name) in allowed:result[name]=value[name]
    result.update(fields(value,('envelope',)))
    if isinstance(value.get('comparison'),dict):
        c=value['comparison'];result['comparison']=fields(c,('b','c','p','difference','n'))
        if isinstance(c.get('diff_ci95'),list) and len(c['diff_ci95'])==2 and all(numeric(n) for n in c['diff_ci95']):result['comparison']['diff_ci95']=c['diff_ci95']
    return result


def project(row):
    value=row.get('mastery_study')
    if row.get('protocol')!='E15' or not isinstance(value,dict) or value.get('schema_version')!=1:return None
    result={'schema_version':1,'run_id':row['run_id'],'started_at':row.get('started_at'),
        'candidate':value.get('candidate') if value.get('candidate') in ARMS else '',
        'baseline':value.get('baseline') if value.get('baseline') in ARMS else '',
        'interpretation':value.get('interpretation') if value.get('interpretation') in ('model_upgrade','procedure_tool_comparison','baseline_retained') else '',
        'decision':value.get('decision') if value.get('decision') in ('held','confirmation_candidate') else 'held',
        'candidate_deployed':False,'official_closed':value.get('official_closed') is True,
        'cost_accounting_complete':value.get('cost_accounting_complete') is True,
        'confirmation_cost_accounting_complete':value.get('confirmation_cost_accounting_complete') is True,
        'blinding_passed':value.get('blinding_passed') is True,
        'report_path':'research/results/E15.md','protocol_path':'research/protocols/E15-solver-mastery-v2.md' if value.get('protocol_version')==2 else 'research/protocols/E15-solver-mastery.md',
        'clarification_path':'research/protocols/E15-solver-mastery-clarification.md'}
    result.update(fields(value,('unique_evaluated','condition_responses','budget_limit_usd','charged_usd','unknown_usage','normalised_usd','estimated_billed_usd','audited_requests','matched_requests','protocol_version')))
    preparation=value.get('preparation',{})
    result['preparation']={**fields(preparation,('invalid_evaluated_questions','invalid_phase_generation_calls','invalid_phase_normalised_usd',
        'invalid_phase_estimated_billed_usd','aborted_reservations','aborted_reservation_upperbound_usd','restored_questions','keys_changed','choices_changed')),
        'confirmation_previously_started':preparation.get('confirmation_previously_started') is True,
        'source_test_roles_preserved':preparation.get('old_confirmation_source_tests_preserved') is True}
    result.update(hashes(value,('manifest_hash','policy_hash','source_hash')))
    split=value.get('split',{});result['split']={'counts':fields(split.get('counts',{}),ROLES),'groups':fields(split.get('groups',{}),ROLES),
        'hashes':hashes(split.get('hashes',{}),ROLES),**fields(split,('total_gmat_records','near_stimulus_links','confirmation_overlap'))}
    result['phases']={}
    for name,p in value.get('phases',{}).items():
        if name not in PHASES:continue
        result['phases'][name]={**fields(p,('registered','evaluated','unique_questions')),'budget_limited':p.get('budget_limited') is True,
            'completed':p.get('completed') is True,'conditions':{a:project_metric(v) for a,v in p.get('conditions',{}).items() if a in ARMS},
            'roles':{r:{a:project_metric(v) for a,v in values.items() if a in ARMS} for r,values in p.get('roles',{}).items() if r in ROLES}}
    return result
