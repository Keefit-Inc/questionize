from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from conftest import ARTICLE, ScriptedLLM, TextJudgeLLM, make_analysis
from questionize.app import create_app
from questionize.config import ProviderConfig, Settings
from questionize.judge import ArgumentJudge
from questionize.mapper import MapPipeline
from questionize.pipeline import ArticleDeclined, QuestionPipeline
from questionize.schemas import ChallengeDraft, MapClaim, MapDraft, MapRequest

WEAKEN = ["If it turned out that accidents also fell on streets without new lanes", "If cyclists liked the lanes",
          "If the lanes were cheap", "If some drivers disliked the lanes", "If other cities also built lanes"]
ASSUME = ["Nothing else that year reduced accidents", "Bike lanes are popular", "Paint is inexpensive",
          "Drivers read signs", "The mayor rides a bike"]
STRENGTHEN = ["If it turned out that cities adding lanes saw drops while similar cities did not", "If lanes were painted green",
              "If the mayor is popular", "If winters vary", "If buses run often"]


def draft() -> MapDraft:
    return MapDraft(
        scheme="causal",
        conclusion=MapClaim(text="Bike lanes everywhere will make all streets safer", anchor="make all streets safer"),
        premises=[MapClaim(text="Accidents on Main Street fell 30% after lanes were added", anchor="reduced traffic accidents by 30 percent " * 4)],
        assumptions=["The lanes, not other changes, caused the drop", "What worked on Main Street works everywhere"],
        challenges=[
            ChallengeDraft(kind="weaken", question="What would most weaken the causal claim?", options=WEAKEN),
            ChallengeDraft(kind="assumption", question="What must the mayor assume?", options=ASSUME),
            ChallengeDraft(kind="strengthen", question="What would most strengthen it?", options=STRENGTHEN),
        ],
    )


def judge() -> ArgumentJudge:
    table = {
        WEAKEN[0]: (-0.8, 0.2), ASSUME[0]: (0.4, 0.9), STRENGTHEN[0]: (0.8, 0.2),
        "Accidents on Main Street fell 30% after lanes were added": (0.6, 0.8),
        "The lanes, not other changes, caused the drop": (0.5, 0.95),
        "What worked on Main Street works everywhere": (0.4, 0.6),
    }
    return ArgumentJudge([TextJudgeLLM(table)], samples_per_judge=3, seed=3)


async def test_map_measures_elements_and_judges_each_challenge():
    primary = ScriptedLLM(ArticleAnalysis=[make_analysis()], MapDraft=[draft()])
    events = []

    async def emit(e):
        events.append(e)

    m = await MapPipeline(primary, judge(), seed=1).run(MapRequest(text=ARTICLE, title="Bike lanes"), emit)

    assert [e["stage"] for e in events] == ["analyze", "mapping", "judge"]
    assert m.scheme == "causal"
    assert m.conclusion.anchor == "make all streets safer"
    assert m.premises[0].anchor == "", "over-long anchors are dropped, not republished"
    assert m.premises[0].necessity.value == 0.8
    assert m.largest_gap == "A1"
    judged = {c.kind: c.judged for c in m.challenges}
    assert judged["weaken"].label == "A" and judged["weaken"].measure == "support_delta"
    assert judged["assumption"].label == "A" and judged["assumption"].measure == "necessity"
    assert judged["strengthen"].label == "A" and judged["strengthen"].first_rate == 1.0
    assert all(len(c.options) == 5 for c in m.challenges)


async def test_unsuitable_pages_are_declined_before_mapping():
    thin = make_analysis().model_copy(update={"suitability": "too_thin", "suitability_reason": "Just a headline."})
    primary = ScriptedLLM(ArticleAnalysis=[thin])
    with pytest.raises(ArticleDeclined):
        await MapPipeline(primary, judge()).run(MapRequest(text=ARTICLE))
    assert [name for name, _ in primary.calls] == ["ArticleAnalysis"]


def test_map_endpoint_streams_the_map():
    p = ProviderConfig("meta", "http://x", "k", "m")
    primary = ScriptedLLM(ArticleAnalysis=[make_analysis()], MapDraft=[draft()])
    pipeline = QuestionPipeline(primary, ScriptedLLM(), judge=judge())
    client = TestClient(create_app(Settings(primary=p, solver=p, internal_token="t"), pipeline))

    r = client.post("/v1/map", json={"text": ARTICLE}, headers={"X-Internal-Token": "t"})
    events = [json.loads(line) for line in r.text.splitlines() if line]
    assert [e["stage"] for e in events][-2:] == ["map", "done"]
    assert events[-2]["map"]["largest_gap"] == "A1"
    assert client.post("/v1/map", json={"text": ARTICLE}).status_code == 401
