"""Private GMAT curriculum partitions; source keys never confer expert authority."""
import collections
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .eval_budget_cr import normalise, private_write, stimulus_grams
from .research_budget import digest


def prepare(library: Path, out: Path):
    if (out/"manifest.json").exists(): raise ValueError("Partitions already frozen")
    original=json.loads(library.read_text())
    items=[i for i in original["items"] if i.get("source_exam","GMAT")=="GMAT"]
    parent=list(range(len(items))); grams=[stimulus_grams(i) for i in items]
    def find(a):
        while parent[a]!=a: parent[a]=parent[parent[a]]; a=parent[a]
        return a
    index=collections.defaultdict(set); links=[]
    for n,values in enumerate(grams):
        counts=collections.Counter(k for token in values for k in index[token])
        for k,count in counts.items():
            denominator=min(len(values),len(grams[k]))
            if denominator>=15 and count/denominator>=.8:
                parent[find(n)]=find(k);links.append([items[n]["library_fingerprint"],items[k]["library_fingerprint"]])
        for token in values:index[token].add(n)
    groups=collections.defaultdict(list)
    for n,i in enumerate(items):groups[find(n)].append(i)
    partitions={n:[] for n in ("official_regression","web_regression","compendium_development","confirmation","held")}
    reasons=[]
    for group in groups.values():
        has_exposed=any(i["library_category"]!="user_document" for i in group)
        group_hash=digest(sorted(i["library_fingerprint"] for i in group))
        for i in group:
            reason=None
            if i['library_category']=='existing_og':role='official_regression'
            elif i['library_category']=='additional_sources':role='web_regression'
            elif i.get('library_material_tier')=='held' or i.get('flagged') or i.get('flags'):
                role='held';reason='source_mapping_or_format'
            elif has_exposed:role='held';reason='near_stimulus_overlap_with_exposed_source'
            else:
                # Entire original source test groups share a role; never split a shared stimulus.
                tests=sorted({x.get('source_test','') for x in group if x['library_category']=='user_document'})
                dev=any(int(digest(t)[:8],16)%4==0 for t in tests)
                role='compendium_development' if dev else 'confirmation'
            q=i['question'];text=q['passage']+'\n'+q['stem']
            if i.get('answer_key') not in list('ABCDE') or [c['label'] for c in q['choices']]!=list('ABCDE'):
                role='held';reason='incomplete_key_or_choices'
            if i['library_category']=='user_document' and re.search(r'bold\s*face|underlin|italic|following (?:figure|diagram)|shaded',text,re.I):
                role='held';reason='source_style_review_required'
            if re.search(r'\b(?:official|correct)\s+answer\s*(?:is|:)\s*[A-E]\b',text,re.I):
                role='held';reason='reference_not_separated'
            record={**i,'e15_role':role,'stimulus_group':group_hash}
            partitions[role].append(record)
            if reason:reasons.append({'fingerprint':i['library_fingerprint'],'reason':reason})
    for role in partitions:partitions[role].sort(key=lambda i:i['library_fingerprint'])
    roles={k:{i['stimulus_group'] for i in v} for k,v in partitions.items()}
    for name in ('official_regression','web_regression','compendium_development'):
        assert not roles[name]&roles['confirmation']
    public={'counts':{k:len(v) for k,v in partitions.items()},'groups':{k:len(roles[k]) for k in roles},
            'hashes':{k:digest([i['library_fingerprint'] for i in v]) for k,v in partitions.items()},
            'held_reasons':dict(collections.Counter(i['reason'] for i in reasons)),
            'near_stimulus_links':len(links),'confirmation_overlap':0,'total_gmat_records':len(items),
            'lsat_used':False,'compendium_reference_status':'supplied_key_only; not independently adjudicated',
            'exposed_cohorts_are_fresh':False}
    manifest={'protocol':'E15','protocol_version':1,'created_at':datetime.now(timezone.utc).isoformat(),
              'library_hash':digest(original),'public':public,'partitions':partitions,'held':reasons,
              'protocol_hash':digest((Path(__file__).resolve().parents[2]/'research/protocols/E15-solver-mastery.md').read_text())}
    private_write(out/'manifest.json',manifest)
    print(json.dumps(public))
    return manifest
