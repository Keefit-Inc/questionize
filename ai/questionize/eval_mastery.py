"""E15 private Solver development, held-out confirmation and broad regression.

python -m questionize.eval_mastery prepare --out PRIVATE --library PRIVATE_LIBRARY
python -m questionize.eval_mastery pilot --out PRIVATE --policy PRIVATE_POLICY
python -m questionize.eval_mastery ogdev --out PRIVATE --policy PRIVATE_POLICY
python -m questionize.eval_mastery docdev --out PRIVATE --policy PRIVATE_POLICY --arms S,P
python -m questionize.eval_mastery select --out PRIVATE --policy PRIVATE_POLICY --candidate P
python -m questionize.eval_mastery confirm --out PRIVATE
python -m questionize.eval_mastery regression --out PRIVATE
"""
import argparse
import asyncio
import json
import random
import subprocess
from dataclasses import replace
from datetime import datetime,timezone
from pathlib import Path

from .eval_budget_cr import REPO,private_write
from .mastery_budget import StudyBudget,StudyBudgetStop
from .mastery_data import prepare
from .mastery_solver import solve_method
from .research_budget import BudgetClient,digest

ARMS={
    'SM':{'model':'muse-spark-1.3','effort':'medium','method':'direct','envelope':.06},
    'S':{'model':'muse-spark-1.3','effort':'high','method':'direct','envelope':.06},
    'P':{'model':'muse-spark-1.3','effort':'high','method':'mechanism','envelope':.06},
    'W':{'model':'muse-wonder-1.0','effort':'high','method':'direct','envelope':.15},
    'PW':{'model':'muse-wonder-1.0','effort':'high','method':'mechanism','envelope':.15},
}


def source_hash():
    return digest({name:Path(__file__).with_name(name+'.py').read_text() for name in
        ('eval_mastery','mastery_data','mastery_solver','mastery_budget','research_budget','source_input','prompts','llm','eval_budget_cr')})


def load_policy(path):
    policy=json.loads(path.read_text())
    if not policy.get('procedures') or policy.get('origin')!='ai_derived_from_private_expert_reference':
        raise ValueError('Missing explicit strategy provenance')
    return policy


def pilot_items(manifest,targets):
    official=manifest['partitions']['official_regression'];hard=[i for i in official if i['entry_id'] in targets]
    if len(hard)!=2:raise ValueError('Expected two privately registered official failures')
    selected=[];covered=set()
    for item in official:
        if item in hard:continue
        if item.get('subtype') not in covered:
            selected.append(item);covered.add(item.get('subtype'))
        if len(selected)==6:break
    return [{**i,'diagnostic_repeat':repeat} for repeat in (1,2) for i in hard]+[{**i,'diagnostic_repeat':1} for i in selected]


def select(root,policy_path,candidate,include=None):
    path=root/'selected.json'
    if path.exists() or (root/'confirm.json').exists():raise ValueError('Final configuration already frozen')
    if not (root/'ogdev.json').exists() or not (root/'docdev.json').exists():raise ValueError('Development cohorts required before final selection')
    policy=load_policy(policy_path);config=ARMS[candidate]
    dev=json.loads((root/'docdev.json').read_text())
    if dev['policy_hash']!=digest(policy) or candidate not in dev['arms']:raise ValueError('Selected candidate was not evaluated with this policy')
    baseline='W' if candidate=='PW' else 'S'
    envelope=max(config['envelope'],ARMS[baseline]['envelope'])
    names=list(dict.fromkeys([baseline,candidate]+(include or [])))
    if any(name not in dev['arms'] for name in names):raise ValueError('All final comparison arms must have development results')
    frozen={'candidate':candidate,'baseline':baseline,'arms':{name:{**ARMS[name],'envelope':envelope} for name in names},
            'policy':policy,'policy_hash':digest(policy),
            'manifest_hash':digest(json.loads((root/'manifest.json').read_text())),
            'selected_at':datetime.now(timezone.utc).isoformat(),'source_hash':source_hash(),
            'interpretation':'model_upgrade' if candidate=='W' else 'procedure_tool_comparison' if candidate in ('P','PW') else 'baseline_retained'}
    private_write(path,frozen);print(json.dumps({k:v for k,v in frozen.items() if k!='policy'}))


async def run_phase(root,phase,policy_path=None,arms=None):
    from .config import load_settings
    manifest=json.loads((root/'manifest.json').read_text())
    if phase in ('confirm','regression'):
        selection=json.loads((root/'selected.json').read_text());policy=selection['policy'];configs=selection['arms']
        if digest(manifest)!=selection['manifest_hash'] or digest(policy)!=selection['policy_hash'] or source_hash()!=selection['source_hash']:
            raise ValueError('Frozen final provenance changed')
        if phase=='confirm':items=manifest['partitions']['confirmation']
        else:
            items=manifest['partitions']['official_regression']+manifest['partitions']['web_regression']
            configs={selection['candidate']:configs[selection['candidate']]}
    else:
        policy=load_policy(policy_path);names=arms or (['SM'] if phase=='effort' else ['S','P','W','PW'] if phase in ('pilot','ogdev') else ['S','P'])
        configs={name:ARMS[name] for name in names}
        items=pilot_items(manifest,policy['diagnostic_targets']) if phase=='pilot' else [i for i in manifest['partitions']['official_regression'] if i.get('split')!='train'] if phase in ('ogdev','effort') else manifest['partitions']['compendium_development']
    path=root/(phase+'.json')
    if path.exists():raise ValueError('Phase already recorded; no selective reruns')
    if not items:raise ValueError('No eligible items')
    run={'phase':phase,'started_at':datetime.now(timezone.utc).isoformat(),'expected':len(items),'arms':configs,
         'policy_hash':digest(policy),'manifest_hash':digest(manifest),'source_hash':source_hash(),
         'git_sha':subprocess.run(['git','rev-parse','HEAD'],cwd=REPO,capture_output=True,text=True).stdout.strip(),
         'rows':[],'budget_limited':False}
    private_write(path,run)
    snapshot=root/'source'/phase;snapshot.mkdir(parents=True,exist_ok=True,mode=0o700)
    for name in ('eval_mastery','mastery_data','mastery_solver','mastery_budget','research_budget','source_input','prompts','llm','eval_budget_cr'):
        source=Path(__file__).with_name(name+'.py');target=snapshot/source.name
        target.write_bytes(source.read_bytes());target.chmod(0o600)
    traces=root/(phase+'-responses.jsonl');traces.touch(mode=0o600,exist_ok=True);traces.chmod(0o600)
    def audit(value):
        with traces.open('a') as handle:handle.write(json.dumps(value,ensure_ascii=False)+'\n')
    provider=load_settings().primary
    clients={name:BudgetClient(replace(provider,model=config['model']),effort=config['effort'],audit=audit) for name,config in configs.items()}
    budget=StudyBudget(root/'budget-state.json');queue=asyncio.Queue()
    for n,item in enumerate(items):queue.put_nowait((n,item))
    lease_amount=sum(c['envelope'] for c in configs.values())
    async def worker():
        while True:
            try:n,item=queue.get_nowait()
            except asyncio.QueueEmpty:return
            try:lease=await budget.reserve(lease_amount)
            except StudyBudgetStop:
                run['budget_limited']=True;queue.task_done();return
            record={'index':n,'fingerprint':item['library_fingerprint'],'stimulus_group':item['stimulus_group'],
                    'role':item['e15_role'],'entry_id':item['entry_id'],'repeat':item.get('diagnostic_repeat',1),'conditions':{}}
            names=list(configs);random.Random(item['library_fingerprint']+str(record['repeat'])).shuffle(names)
            for name in names:
                c=configs[name];record['conditions'][name]=await solve_method(clients[name],item,c['method'],policy,c['envelope'])
            metrics=[c for result in record['conditions'].values() for c in result['calls']]
            await budget.finish(lease,metrics)
            run['rows'].append(record);private_write(path,run);queue.task_done()
            print(json.dumps({'phase':phase,'completed':len(run['rows']),'registered':len(items),
                'correct':{name:sum(r['conditions'][name]['correct'] for r in run['rows']) for name in configs},
                'errors':sum(bool(v['error']) for r in run['rows'] for v in r['conditions'].values()),
                'charged_usd':round(budget.spent,4)}),flush=True)
    try:await asyncio.gather(*(worker() for _ in range(min(6,len(items)))))
    finally:
        for client in clients.values():await client.close()
    run['finished_at']=datetime.now(timezone.utc).isoformat();run['budget']=json.loads((root/'budget-state.json').read_text());private_write(path,run)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('prepare','pilot','effort','ogdev','docdev','select','confirm','regression'))
    p.add_argument('--out',type=Path,required=True);p.add_argument('--library',type=Path);p.add_argument('--policy',type=Path)
    p.add_argument('--arms');p.add_argument('--candidate',choices=ARMS);p.add_argument('--include-arms');args=p.parse_args();root=args.out.expanduser().resolve()
    if root.is_relative_to(REPO):raise ValueError('All private research artifacts must remain outside Git')
    if args.action=='prepare':prepare(args.library,root)
    elif args.action=='select':select(root,args.policy,args.candidate,args.include_arms.split(',') if args.include_arms else None)
    else:asyncio.run(run_phase(root,args.action,args.policy,args.arms.split(',') if args.arms else None))


if __name__=='__main__':main()
