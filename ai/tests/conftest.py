"""A scripted stand-in for the LLM so the pipeline can be tested offline."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from questionize.schemas import (  # noqa: E402
    Argument,
    ArticleAnalysis,
    Choice,
    ChoiceRationale,
    CriticResult,
    Question,
    SolverResult,
)

ARTICLE = (
    "City officials announced that the new bike lanes on Main Street reduced traffic accidents by 30 percent "
    "in their first year. The mayor concluded that expanding bike lanes citywide will make all streets safer. "
    "Critics note that the same year saw a new speed camera program and an unusually mild winter. "
) * 3


def make_analysis() -> ArticleAnalysis:
    return ArticleAnalysis(
        suitability="suitable",
        suitability_reason="A news report with a clear causal argument.",
        main_point="Bike lanes are credited with a drop in accidents.",
        author_purpose="To report a policy claim and its critics.",
        reading_level="medium",
        arguments=[
            Argument(
                conclusion="Citywide bike lanes will make all streets safer.",
                premises=["Accidents on Main Street fell 30% after bike lanes."],
                unstated_assumptions=["No other factor caused the drop."],
                potential_flaws=["Ignores speed cameras and weather as alternative causes."],
            )
        ],
        rc_focus_points=["Critics cite confounding factors."],
        sc_candidate_sentences=["City officials announced that the new bike lanes reduced accidents."],
        content_flags=[],
    )


def make_question(correct: str = "B", qtype: str = "CR") -> Question:
    labels = "ABCDE"
    return Question(
        type=qtype,
        subtype="weaken",
        passage="Accidents fell 30% after bike lanes were added, so bike lanes will make all streets safer.",
        stem="Which of the following, if true, most seriously weakens the argument?",
        # Deliberately out of order to exercise normalization.
        choices=[Choice(label=l, text=f"Option {l}") for l in reversed(labels)],
        correct_label=correct,
        explanation="B names an alternative cause.",
        choice_rationales=[
            ChoiceRationale(label=l, rationale=f"Why {l}", trap="correct" if l == correct else "out_of_scope")
            for l in labels
        ],
        skill="Alternative causes",
        source_anchor="reduced traffic accidents by 30 percent",
    )


class ScriptedLLM:
    """Returns queued responses per schema; records every call."""

    def __init__(self, model: str = "fake-model", **queues):
        self.model = model
        self.queues = {k: list(v) for k, v in queues.items()}
        self.calls: list[tuple[str, str]] = []

    async def complete(self, system, user, schema, *, temperature=0.4):
        self.calls.append((schema.__name__, user))
        queue = self.queues.get(schema.__name__)
        if not queue:
            raise AssertionError(f"Unexpected call for {schema.__name__}")
        item = queue.pop(0) if len(queue) > 1 else queue[0]
        return item() if callable(item) else item


@pytest.fixture
def analysis():
    return make_analysis()


def passing_critic() -> CriticResult:
    return CriticResult(
        verdict="pass", unique_answer=True, faithful_to_source=True, distractor_quality=4, issues=[], revision_guidance=""
    )


def solver(label: str, conf: float = 0.9) -> SolverResult:
    return SolverResult(answer_label=label, confidence=conf, reasoning="elimination")
