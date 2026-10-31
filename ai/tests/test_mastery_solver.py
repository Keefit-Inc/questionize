import asyncio
import json
from types import SimpleNamespace

import pytest

from questionize.mastery_budget import StudyBudget,StudyBudgetStop
from questionize.mastery_solver import RateClaim,rate_witness,solve_method
from questionize.research_budget import BudgetFailure,MODEL_RATES,price,output_limit


def claim(**extra):
    return RateClaim(earlier_percent=38,later_percent=65,earlier_anchor='38%',later_anchor='65%',
        earlier_denominator=None,later_denominator=None,denominators_equal=False,denominator_anchor='',conclusion_is_absolute_count=True,**extra)


def test_arithmetic_witness_is_exact_and_source_anchored():
    c=claim();w=rate_witness(c,'First 38%, later 65% of applicants.')
    assert w['status']=='counterexample_checked' and w['earlier_count']>w['later_count']
    assert all(w['checks'].values()) and not w['semantic_mapping_certified']
    assert rate_witness(c,'No such percentages here')['status']=='unverified_mapping'
    c=c.model_copy(update={'denominators_equal':True,'denominator_anchor':'same number'})
    assert rate_witness(c,'First 38%, later 65% from the same number of applicants')['status']=='same_denominator_conditional'


@pytest.mark.asyncio
async def test_optional_repair_failure_keeps_completed_answer_and_does_not_see_key():
    calls=[]
    class Fake:
        async def complete(self,system,user,schema,allowance):
            assert 'PRIVATE_REFERENCE' not in system+user and 'answer_key' not in user
            metric={'normalised_usd':.01,'allowance_usd':allowance,'generation_calls':1,'usage_complete':True}
            calls.append(metric)
            if len(calls)==2:raise BudgetFailure('incomplete_response',metric)
            return schema(answer_label='D',confidence=.8,reasoning='The percentage alone does not determine the number.',task='flaw',
                          task_operator='logical flaw',conclusion_anchor='number increased',new_assumptions_in_selected_answer='',
                          option_audits=[{'label':label,'relation_to_task':'check','extra_assumption_needed':''} for label in 'ABCDE'],numeric_claim=claim()),metric
    item={'question':{'passage':'Initially 38%, later 65%. The number increased.','stem':'Which identifies the flaw?',
                    'choices':[{'label':l,'text':'Option '+l} for l in 'ABCDE'],'local_reference':{'key':'PRIVATE_REFERENCE'}},
          'answer_key':'D','official_explanation':'PRIVATE_REFERENCE'}
    result=await solve_method(Fake(),item,'mechanism',{'procedures':['Check denominator.']},.06)
    assert result['correct'] and result['answer']=='D' and result['repair_error']=='incomplete_response'
    assert result['error'] is None and len(result['calls'])==2


@pytest.mark.asyncio
async def test_concurrent_budget_waits_for_unused_reservations_then_stops(tmp_path):
    b=StudyBudget(tmp_path/'budget.json',limit=.1);a=await b.reserve(.08)
    waiting=asyncio.create_task(b.reserve(.08));await asyncio.sleep(0)
    assert not waiting.done()
    await b.finish(a,[{'normalised_usd':.01,'generation_calls':1,'usage_complete':True}])
    second=await waiting
    await b.finish(second,[{'normalised_usd':.08,'generation_calls':1,'usage_complete':True}])
    with pytest.raises(StudyBudgetStop):await b.reserve(.02)
    assert b.spent<=.1


def test_registered_model_rates_do_not_price_wonder_as_spark():
    assert price(1000,1000,rates=MODEL_RATES['muse-wonder-1.0'])==.024
    assert output_limit(.03,1000,rates=MODEL_RATES['muse-wonder-1.0'])==1300
