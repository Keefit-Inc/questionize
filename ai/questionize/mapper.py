"""Map → Challenge (docs/ARCHITECTURE.md §5.0).

Reconstructs an article's main argument, measures how much each stated premise and unstated
assumption carries it with the Argument Judge, and builds three critical questions whose candidate
answers the judge measures too. The reader answers each challenge before the judged answer is
revealed; nothing here grades the author or checks facts.
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import Any

from . import prompts
from .judge import ArgumentJudge, measurements, rank
from .llm import StructuredLLM
from .pipeline import ArticleDeclined
from .schemas import (
    LABELS,
    ArgumentMap,
    ArticleAnalysis,
    Challenge,
    ChallengeDraft,
    ChallengeOption,
    JudgedAnswer,
    MapClaim,
    MapDraft,
    MapElement,
    MapRequest,
)

Emit = Callable[[dict[str, Any]], Awaitable[None]]

MAX_ANCHOR_WORDS = 20
# What decides the best answer for each challenge kind.
CHALLENGE_MEASURES = {"weaken": ("support_delta", "min"), "strengthen": ("support_delta", "max"), "assumption": ("necessity", "max")}
ELEMENTS_STEM = "How does each statement bear on this argument?"


async def _noop(_: dict[str, Any]) -> None:
    return None


class MapPipeline:
    def __init__(self, primary: StructuredLLM, judge: ArgumentJudge, seed: int | None = None):
        self.primary = primary
        self.judge = judge
        self.rng = random.Random(seed)

    async def run(self, req: MapRequest, emit: Emit = _noop) -> ArgumentMap:
        await emit({"stage": "analyze", "message": "Reading the argument"})
        analysis = await self.primary.complete(
            prompts.ANALYST_SYSTEM, prompts.analyst_user(req.title, req.text, req.selection), ArticleAnalysis, temperature=0.2
        )
        if analysis.suitability != "suitable":
            raise ArticleDeclined(analysis)

        await emit({"stage": "mapping", "message": "Reconstructing the conclusion, premises and assumptions"})
        draft = await self.primary.complete(
            prompts.MAPPER_SYSTEM, prompts.mapper_user(req.title, req.text, req.selection, analysis), MapDraft, temperature=0.3
        )

        await emit({"stage": "judge", "message": "Argument Judge measuring what the argument rests on"})
        argument = prompts.argument_text(draft.conclusion.text, [p.text for p in draft.premises])
        elements_task = self._elements(argument, draft)
        challenge_tasks = [self._challenge(i, argument, c) for i, c in enumerate(draft.challenges)]
        (premises, assumptions), *challenges = await asyncio.gather(elements_task, *challenge_tasks)

        largest_gap = max(assumptions, key=lambda a: a.necessity.value).id
        return ArgumentMap(
            judge_version=self.judge.version,
            scheme=draft.scheme,
            conclusion=_trim_anchor(draft.conclusion),
            premises=premises,
            assumptions=assumptions,
            largest_gap=largest_gap,
            challenges=challenges,
        )

    async def _elements(self, argument: str, draft: MapDraft) -> tuple[list[MapElement], list[MapElement]]:
        premises = [(f"P{i + 1}", _trim_anchor(p)) for i, p in enumerate(draft.premises)]
        assumptions = [(f"A{i + 1}", MapClaim(text=t)) for i, t in enumerate(draft.assumptions)]
        options = [(id_, claim.text) for id_, claim in premises + assumptions]
        samples = await self.judge.sample(argument, ELEMENTS_STEM, options)

        def element(id_: str, claim: MapClaim) -> MapElement:
            support, necessity = measurements(samples, id_, self.rng)
            return MapElement(id=id_, text=claim.text, anchor=claim.anchor, support_delta=support, necessity=necessity)

        return [element(*p) for p in premises], [element(*a) for a in assumptions]

    async def _challenge(self, index: int, argument: str, draft: ChallengeDraft) -> Challenge:
        options = list(zip(LABELS, draft.options))
        samples = await self.judge.sample(argument, draft.question, options)
        measure, direction = CHALLENGE_MEASURES[draft.kind]
        best, first_rate, margin, runner_up = rank(samples, measure, direction, self.rng)
        rated = []
        for label, text in options:
            support, necessity = measurements(samples, label, self.rng)
            rated.append(ChallengeOption(label=label, text=text, support_delta=support, necessity=necessity))
        return Challenge(
            index=index, kind=draft.kind, question=draft.question, options=rated,
            judged=JudgedAnswer(label=best, measure=measure, first_rate=first_rate, margin=margin, runner_up=runner_up),
        )


def _trim_anchor(claim: MapClaim) -> MapClaim:
    # Anchors only locate a claim on the page; long quotes are dropped rather than republished.
    return claim if len(claim.anchor.split()) <= MAX_ANCHOR_WORDS else claim.model_copy(update={"anchor": ""})
