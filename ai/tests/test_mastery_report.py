import json

from questionize.mastery_report import project
from questionize.scoreboard import render_data


def test_mastery_export_never_forwards_questions_keys_or_private_strategy():
    value={'schema_version':1,'protocol_version':2,'candidate':'W','baseline':'S','interpretation':'model_upgrade','decision':'held',
        'official_closed':False,'candidate_deployed':True,'policy':'PRIVATE_SENTINEL','manifest_hash':'a'*64,
        'split':{'counts':{'confirmation':363,'private_source':'PRIVATE_SENTINEL'},'hashes':{'confirmation':'b'*64}},
        'preparation':{'restored_questions':76,'local_path':'PRIVATE_SENTINEL','keys_changed':0},
        'phases':{'confirm':{'registered':363,'evaluated':363,'conditions':{'W':{'n':363,'correct':360,'accuracy':360/363,
            'original_question':'PRIVATE_SENTINEL','model':'muse-wonder-1.0','comparison':{'b':2,'c':0,'diff_ci95':[0,.02]}},
            'PRIVATE_SENTINEL':{'n':1}},'private_results':'PRIVATE_SENTINEL'}}}
    row={'run_id':'e15-example','protocol':'E15','started_at':'2026-10-30T00:00:00Z','capabilities':[],'summary':{},'mastery_study':value}
    exported=project(row)
    assert 'PRIVATE_SENTINEL' not in json.dumps(exported)
    assert exported['candidate_deployed'] is False
    assert exported['preparation']['restored_questions']==76
    assert exported['protocol_path'].endswith('-v2.md')
    assert render_data([row])['mastery_studies']==[exported]


def test_comparison_intervals_cannot_smuggle_nested_private_strings():
    row={'run_id':'e15','protocol':'E15','mastery_study':{'schema_version':1,'phases':{'confirm':{'conditions':{'S':{
        'comparison':{'diff_ci95':['PRIVATE_SENTINEL',{'private':'PRIVATE_SENTINEL'}]}}}}}}}
    assert 'PRIVATE_SENTINEL' not in json.dumps(project(row))
