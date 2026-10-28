from __future__ import annotations

import random

from conftest import ARTICLE, ScriptedLLM, make_analysis, make_question, passing_critic, solver
from questionize import levels
from questionize.pipeline import QuestionPipeline, plan_slots
from questionize.schemas import GenerateRequest


def test_every_level_has_a_brief_and_in_scope_subtypes():
    for level_id, lv in levels.LEVELS.items():
        text = levels.brief(level_id)
        assert lv.label in text and "Language:" in text
        assert set(levels.subtypes(level_id, "CR")) <= {"weaken", "strengthen", "assumption", "flaw", "evaluate", "inference"}
    assert "RI.4.8" in levels.brief("elementary")
    assert levels.level("unknown").id == levels.DEFAULT_LEVEL


def test_young_learners_only_get_the_question_types_for_their_grade():
    req = GenerateRequest(text=ARTICLE, types=["CR", "RC"], count_per_type=3, level="elementary")
    slots = plan_slots(req, make_analysis(), random.Random(1))
    assert {s for f, s in slots if f == "CR"} <= {"strengthen", "weaken", "inference"}
    assert {s for f, s in slots if f == "RC"} <= {"main_idea", "detail", "inference"}


async def test_writer_and_critic_are_told_who_the_question_is_for():
    primary = ScriptedLLM(ArticleAnalysis=[make_analysis()], Question=[make_question("B")], CriticResult=[passing_critic()])
    out = await QuestionPipeline(primary, ScriptedLLM(SolverResult=[solver("B")])).run(
        GenerateRequest(text=ARTICLE, types=["CR"], level="middle")
    )
    assert out.questions
    prompts_by_schema = {name: user for name, user in primary.calls}
    assert "AUDIENCE LEVEL: Grades 6-8" in prompts_by_schema["Question"]
    assert "AUDIENCE LEVEL: Grades 6-8" in prompts_by_schema["CriticResult"]
    assert out.questions[0].question.scene == "everyday"
