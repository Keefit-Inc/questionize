"""Argument Judge: quantifies how each option bears on an argument (docs/ARCHITECTURE.md §4.5).

Each judge model rates every option on two measures without seeing the intended key:

    support_delta  -1..1  how far, and which way, the conclusion's likelihood moves if the option is true
    necessity       0..1  the probability the argument falls apart if the option is false

Options are shuffled for every sample to wash out position bias. Samples from all judges are
pooled and bootstrapped into a value and interval per option, how often the key ranks first,
and the margin over the runner-up. Close calls get one round of extra samples before a verdict.
"""

from __future__ import annotations

import asyncio
import random
import statistics
from collections.abc import Sequence

from . import prompts
from .llm import StructuredLLM
from .schemas import LABELS, JudgeRatings, JudgeResult, Measurement, OptionJudgement, Question

JUDGE_VERSION = "aj-0.1"

# Which measure identifies the key for each CR sub-type, and whether the key maximizes or minimizes it.
SUBTYPE_MEASURES: dict[str, tuple[str, str]] = {
    "strengthen": ("support_delta", "max"),
    "weaken": ("support_delta", "min"),
    "assumption": ("necessity", "max"),
}

BOOTSTRAP_ROUNDS = 400
DISPLAY_LETTERS = "ABCDEFGH"

Sample = dict[str, tuple[float, float]]  # label -> (support_delta, necessity)


class ArgumentJudge:
    def __init__(
        self,
        judges: Sequence[StructuredLLM],
        samples_per_judge: int = 3,
        min_first_rate: float = 0.9,
        min_margin: float = 0.15,
        seed: int | None = None,
    ):
        # The same model listed twice adds no independence.
        unique: dict[str, StructuredLLM] = {}
        for judge in judges:
            unique.setdefault(judge.model, judge)
        self.judges = list(unique.values())
        self.samples_per_judge = samples_per_judge
        self.min_first_rate = min_first_rate
        self.min_margin = min_margin
        self.rng = random.Random(seed)

    @property
    def version(self) -> str:
        return f"{JUDGE_VERSION}:" + "+".join(j.model for j in self.judges)

    async def judge(self, q: Question) -> JudgeResult:
        measure, direction = SUBTYPE_MEASURES.get(q.subtype, (None, None))
        options = [(c.label, c.text) for c in q.choices]
        samples = await self.sample(q.passage, q.stem, options)
        result = self._summarize(q, samples, measure, direction)
        if result.verdict == "ambiguous" and result.key_first_rate >= 0.5:
            # Close call: look again before deciding.
            samples += await self.sample(q.passage, q.stem, options)
            result = self._summarize(q, samples, measure, direction)
        return result

    async def sample(self, passage: str, stem: str, options: list[tuple[str, str]]) -> list[Sample]:
        """Ratings for any 2-8 labeled statements, keyed by the caller's labels, from every judge."""
        tasks = [self._one(judge, passage, stem, options) for judge in self.judges for _ in range(self.samples_per_judge)]
        samples = [s for s in await asyncio.gather(*tasks) if len(s) == len(options)]
        if not samples:
            raise ValueError("Argument Judge returned no complete samples")
        return samples

    async def _one(self, judge: StructuredLLM, passage: str, stem: str, options: list[tuple[str, str]]) -> Sample:
        order = list(options)
        self.rng.shuffle(order)
        letters = DISPLAY_LETTERS[: len(order)]
        # Displayed letter -> caller's label.
        shown = {letter: label for letter, (label, _) in zip(letters, order)}
        out = await judge.complete(
            prompts.JUDGE_SYSTEM,
            prompts.judge_user(passage, stem, [(letter, text) for letter, (_, text) in zip(letters, order)]),
            JudgeRatings,
            temperature=0.7,
        )
        return {shown[r.option]: (r.support_delta, r.necessity) for r in out.ratings if r.option in shown}

    def _summarize(self, q: Question, samples: list[Sample], measure: str | None, direction: str | None) -> JudgeResult:
        options = [
            OptionJudgement(
                label=label,
                support_delta=_measurement([s[label][0] for s in samples], self.rng),
                necessity=_measurement([s[label][1] for s in samples], self.rng),
            )
            for label in LABELS
        ]
        if measure is None:
            return JudgeResult(
                judge_version=self.version, measure=None, direction=None, options=options, key_first_rate=0.0,
                margin=0.0, runner_up=None, judges=[j.model for j in self.judges], samples=len(samples),
                verdict="not_applicable",
            )

        index = 0 if measure == "support_delta" else 1
        sign = 1.0 if direction == "max" else -1.0
        first, margins, runners = 0, [], []
        for _ in range(BOOTSTRAP_ROUNDS):
            draw = [self.rng.choice(samples) for _ in samples]
            score = {label: sign * statistics.fmean(s[label][index] for s in draw) for label in LABELS}
            best_other = max((label for label in LABELS if label != q.correct_label), key=score.__getitem__)
            margins.append(score[q.correct_label] - score[best_other])
            runners.append(best_other)
            first += score[q.correct_label] > score[best_other]

        key_first_rate = first / BOOTSTRAP_ROUNDS
        margin = statistics.median(margins)
        if key_first_rate >= self.min_first_rate and margin >= self.min_margin:
            verdict = "pass"
        elif key_first_rate < 0.5:
            verdict = "wrong_key"
        else:
            verdict = "ambiguous"
        return JudgeResult(
            judge_version=self.version, measure=measure, direction=direction, options=options,
            key_first_rate=round(key_first_rate, 3), margin=round(margin, 3),
            runner_up=max(set(runners), key=runners.count), judges=[j.model for j in self.judges],
            samples=len(samples), verdict=verdict,
        )


def _measurement(values: list[float], rng: random.Random) -> Measurement:
    means = sorted(statistics.fmean(rng.choice(values) for _ in values) for _ in range(BOOTSTRAP_ROUNDS))
    low, high = means[int(0.05 * len(means))], means[int(0.95 * len(means)) - 1]
    return Measurement(value=round(statistics.fmean(values), 3), ci_low=round(low, 3), ci_high=round(high, 3))


def judge_feedback(result: JudgeResult) -> str:
    """Revision guidance when the judge does not clear an item."""
    if result.verdict == "wrong_key":
        return (
            f"The Argument Judge rates option {result.runner_up} above the keyed answer on {result.measure}. "
            "Either make the key unambiguously best or fix that option."
        )
    return (
        f"The keyed answer beats option {result.runner_up} by only {result.margin:.2f} on {result.measure} "
        f"(key first in {result.key_first_rate:.0%} of resamples). Widen the gap: make {result.runner_up} "
        "clearly weaker on that dimension or the key clearly stronger."
    )


def measurements(samples: list[Sample], label: str, rng: random.Random) -> tuple[Measurement, Measurement]:
    """(support_delta, necessity) with intervals for one label."""
    return (
        _measurement([s[label][0] for s in samples], rng),
        _measurement([s[label][1] for s in samples], rng),
    )


def rank(samples: list[Sample], measure: str, direction: str, rng: random.Random) -> tuple[str, float, float, str]:
    """The best label by a measure, the share of resamples where it stays best, its margin and the runner-up."""
    index = 0 if measure == "support_delta" else 1
    sign = 1.0 if direction == "max" else -1.0
    labels = list(samples[0])
    mean = {label: sign * statistics.fmean(s[label][index] for s in samples) for label in labels}
    best = max(labels, key=mean.__getitem__)
    runner_up = max((label for label in labels if label != best), key=mean.__getitem__)
    first, margins = 0, []
    for _ in range(BOOTSTRAP_ROUNDS):
        draw = [rng.choice(samples) for _ in samples]
        score = {label: sign * statistics.fmean(s[label][index] for s in draw) for label in labels}
        other = max(score[label] for label in labels if label != best)
        margins.append(score[best] - other)
        first += score[best] > other
    return best, round(first / BOOTSTRAP_ROUNDS, 3), round(statistics.median(margins), 3), runner_up
